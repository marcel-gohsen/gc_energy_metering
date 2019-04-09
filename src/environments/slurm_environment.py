import os
import os.path as path

import subprocess
import time

from error_handling.error_handler import ErrorHandler
from environments.environment import Environment


class SlurmEnvironment(Environment):
    def __init__(self, data_collector):
        self.slurm_execution_root = "../data/slurm"

        if not path.exists(self.slurm_execution_root) or not path.isdir(self.slurm_execution_root):
            os.makedirs(self.slurm_execution_root)

        self.bench_path = None

        self.tftp_root = "/srv/tftpboot/benchmarks/"
        self.tftp_bench_root = None
        self.tftp_bench_perf_root = None

        self.current_run = None
        self.data_collector = data_collector

    @staticmethod
    def __exec_cmd__(command_array, callback_out=None, shell=False):
        process = subprocess.Popen(command_array,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=shell)

        out, err = process.communicate()

        status = process.returncode
        try:
            if status != 0:
                raise RuntimeError

            out_string = out.decode("utf-8")

            if callback_out is not None:
                callback_out(out_string)

            return out_string
        except RuntimeError as exc:
            ErrorHandler.handle("Env",
                                "Execution returned with error: \"" + err.decode("utf-8").replace("\n", "") + "\"",
                                exc, terminate=False)

    def execute(self, runs, buffer_size=100):
        self.tftp_bench_root = path.join(self.tftp_root, runs[0].benchmark.name)
        self.tftp_bench_perf_root = path.join(self.tftp_bench_root, "performance")

        self.current_run = runs[0]

        self.init_job_execution()

        data_entries_per_node = 0

        for run in runs:
            self.current_run = run

            self.create_job_submission_script()
            self.create_slurm_job_script(run.repetitions, run.nodes)
            self.create_cleanup_script()
            self.create_cleanup_job_script(run.nodes)

            self.create_workload_script(run.get_exc_cmd())

            self.__exec_cmd__(["/bin/bash", path.join(self.bench_path, run.benchmark.name + "-run.sh")])
            print("[Slurm] Submitted job run "+str(run.id))
            self.wait_for_completion(run.benchmark.name)

            data_entries_per_node += run.repetitions

            if data_entries_per_node >= buffer_size:
                self.fetch_and_clean()
                data_entries_per_node = 0

        if data_entries_per_node > 0:
            self.fetch_and_clean()

    def job_is_running(self, job_name):
        out = self.__exec_cmd__(["squeue", "-h", "--name=" + job_name])
        lines = out.split("\n")

        # print("\r[Slurm] Pending tasks: " + str(len(lines) - 1), end="")

        return len(lines) - 1 != 0

    def init_job_execution(self):
        print("[Slurm] Init job execution")
        self.bench_path = path.join(self.slurm_execution_root, self.current_run.benchmark.name)
        os.makedirs(self.bench_path, exist_ok=True)

        os.makedirs(self.tftp_bench_perf_root, exist_ok=True)
        os.system("rm -f " + path.join(self.tftp_bench_perf_root, "*"))

    def fetch_and_clean(self):
        self.wait_for_completion(self.current_run.benchmark.name)

        self.__exec_cmd__(["sbatch", path.join(self.bench_path, self.current_run.benchmark.name + "-cleanup-job.sh")])
        print("[Slurm] Submitted cleanup job")

        self.wait_for_completion("cleanup")
        self.data_collector.collect(self.tftp_bench_perf_root)

    def wait_for_completion(self, job_name):
        print("[Slurm] Wait for job completion")
        while self.job_is_running(job_name):
            time.sleep(1)

    def create_job_submission_script(self):
        job_name = self.current_run.benchmark.name
        with open(path.join(self.bench_path, job_name + "-run.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            out_file.write("pushd " + self.bench_path + "\n")

            if self.current_run.benchmark.resources is not None:
                for key, value in self.current_run.benchmark.resources.items():
                    out_file.write("cp " + value + " " + self.tftp_bench_root + "\n")

            out_file.write("cp " + job_name + "-workload.sh " + self.tftp_bench_root + "\n")
            out_file.write("cp " + job_name + "-cleanup.sh " + self.tftp_bench_root + "\n\n")
            out_file.write("# <PARALLEL EXECUTION>\n")
            out_file.write("sbatch " + job_name + "-slurm-job.sh\n")
            out_file.write("popd")

    def create_slurm_job_script(self, num_repetitions, num_nodes):
        job_name = self.current_run.benchmark.name
        array = "1-" + str(num_repetitions)

        with open(path.join(self.bench_path, job_name + "-slurm-job.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            out_file.write("# <SLURM PARAMETER>\n")
            out_file.write("#SBATCH --job-name=" + job_name + "\n")
            out_file.write("#SBATCH --array=" + array + "\n")
            out_file.write("#SBATCH --nodes=" + str(num_nodes) + "\n")
            out_file.write("#SBATCH --output=%x-%N.out\n")
            out_file.write("#SBATCH --error=%x-%N.err\n")
            out_file.write("#SBATCH --chdir=/home/iss/benchmarks\n\n")

            out_file.write("# <DATA PREPARATION>\n")
            out_file.write("srun mkdir -p " + job_name + "\n")
            out_file.write("cd " + job_name + "\n")

            if self.current_run.benchmark.resources is not None:
                for key, value in self.current_run.benchmark.resources.items():
                    out_file.write(
                        "srun tftp samoa.medien.uni-weimar.de -c get " + path.join(self.tftp_bench_root, value) + "\n"
                    )

            out_file.write(
                "srun tftp samoa.medien.uni-weimar.de -c get " + path.join(self.tftp_bench_root, job_name + "-workload.sh") + "\n")
            out_file.write(
                "srun tftp samoa.medien.uni-weimar.de -c get " + path.join(self.tftp_bench_root, job_name + "-cleanup.sh") + "\n\n")

            out_file.write("# <JOB EXECUTION>\n")
            out_file.write("srun /bin/bash " + job_name + "-workload.sh\n\n")

    def create_cleanup_job_script(self, num_nodes):
        job_name = self.current_run.benchmark.name
        with open(path.join(self.bench_path, job_name + "-cleanup-job.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            out_file.write("# <SLURM PARAMETER>\n")
            out_file.write("#SBATCH --job-name=cleanup\n")
            out_file.write("#SBATCH --nodes=" + str(num_nodes) + "\n")
            out_file.write("#SBATCH --ntasks-per-node=1\n")
            out_file.write("#SBATCH --output=%x-%N.out\n")
            out_file.write("#SBATCH --error=%x-%N.err\n")
            out_file.write("#SBATCH --chdir=/home/iss/benchmarks/" + self.current_run.benchmark.name + "\n\n")

            out_file.write("srun /bin/bash " + job_name + "-cleanup.sh")

    def create_cleanup_script(self):
        job_name = self.current_run.benchmark.name
        with open(path.join(self.bench_path, job_name + "-cleanup.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            out_file.write(
                "tftp samoa.medien.uni-weimar.de -c put $(realpath *.ldjson) " + path.join(self.tftp_bench_perf_root, "$(ls *.ldjson)") + "\n")
            out_file.write("rm *.ldjson")

    def create_workload_script(self, job_command):
        job_name = self.current_run.benchmark.name
        timestamp = "date +%d/%m/%Y\" \"%H:%M:%S\" \"%N"

        with open(path.join(self.bench_path, job_name + "-workload.sh"), "w") as script_file:
            script_file.write("#!/bin/bash\n\n")
            script_file.write("host=$(hostname)\n")
            script_file.write("outfile=\"${SLURM_JOB_NAME}-${host}-measures.ldjson\"\n\n")
            script_file.write("begin=$(" + timestamp + ")\n")
            script_file.write(job_command + "\n")
            script_file.write("end=$(" + timestamp + ")\n\n")

            script_file.write("echo \"{\\\"slurm_job_id\\\":\\\"${SLURM_ARRAY_JOB_ID}\\\", "
                              "\\\"run_spec_id\\\":\\\"" + str(self.current_run.id) + "\\\", "
                              "\\\"sw_config_id\\\":\\\"" + str(self.current_run.sw_config.id) + "\\\", "                                                                                             
                              "\\\"repetition\\\":\\\"${SLURM_ARRAY_TASK_ID}\\\", "
                              "\\\"host\\\":\\\"${host}\\\", "
                              "\\\"command\\\":\\\"" + job_command + "\\\", "
                              "\\\"begin\\\":\\\"${begin}\\\", "
                              "\\\"end\\\":\\\"${end}\\\"}\" "
                              "| tee -a \"${outfile}\"\n\n")