import os
import os.path as path

import subprocess
import time
import getpass

from utility import path_handler
from error_handling.error_handler import ErrorHandler
from environments.environment import Environment
from settings import settings
import re


class SlurmEnvironment(Environment):
    def __init__(self, data_collector=None):
        if not path.exists(path_handler.slurm_script_root) or not path.isdir(path_handler.slurm_script_root):
            os.makedirs(path_handler.slurm_script_root)

        self.data_collector = data_collector
        self.benchmark = None
        self.current_job_id = None

    @staticmethod
    def __exec_cmd__(command_array, callback_out=None, shell=False, handle_err=True):
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
            if handle_err:
                ErrorHandler.handle("Env",
                                    "Execution returned with error: \"" + err.decode("utf-8").replace("\n", "") + "\"",
                                    exc, terminate=False)

    def collect_job_id(self, prompt_out):
        for line in prompt_out.split("\n"):
            if "Submitted batch job" in line:
                self.current_job_id = line.replace("Submitted batch job ", "")

    def execute(self, benchmark):
        self.benchmark = benchmark
        self.init_job_execution()
        self.create_cleanup_job_script()
        self.create_cleanup_script()

        array_id = 1
        for run in benchmark.runs:
            real_script_path = None
            for i in range(settings.RUN_REPETITIONS):
                script_file_path = path.join(path_handler.slurm_script_bench_root,
                                             settings.BENCHMARK["name"] + "-workload-" + str(array_id) + ".sh")
                # if i == 0:
                real_script_path = self.create_workload_script(script_file_path, run)
                # else:
                #     print("CREATE SYMLINK " + real_script_path + " -> " + script_file_path)
                #     os.symlink(real_script_path, script_file_path)
                array_id += 1

        self.create_job_submission_script()
        self.create_slurm_job_script(array_id - 1)

        self.__exec_cmd__(["/bin/bash",
                           path.join(path_handler.slurm_script_bench_root, settings.BENCHMARK["name"] + "-run.sh")],
                          callback_out=self.collect_job_id)
        print("[Slurm] Submitted array job")

        time.sleep(1)
        print("[Slurm] Enter monitoring loop")
        start_time = time.time()

        while self.job_is_pending(settings.BENCHMARK["name"]):
            if time.time() - start_time >= settings.DATA_BUFFER_TIME:
                self.__exec_cmd__(["scontrol", "hold", self.current_job_id], handle_err=False)

                self.fetch_and_clean()
                self.__exec_cmd__(["scontrol", "release", self.current_job_id], handle_err=False)
                start_time = time.time()

        self.fetch_and_clean()

    def job_is_running(self, job_name):
        out = self.__exec_cmd__(["squeue", "-h", "--name=" + job_name, "--partition=" + settings.SLURM_PARTITION])
        lines = out.split("\n")

        num_jobs = 0
        for line in lines:
            args = re.compile("[ ]+").split(line)

            if len(args) == 9:
                if args[5] == "R":
                    num_jobs += 1

        return num_jobs != 0

    def job_is_pending(self, job_name):
        out = self.__exec_cmd__(["squeue", "-h", "--name=" + job_name, "--partition=" + settings.SLURM_PARTITION])
        lines = out.split("\n")

        return len(lines) - 1 != 0

    def init_job_execution(self):
        print("[Slurm] Init job execution")
        os.makedirs(path_handler.slurm_script_bench_root, exist_ok=True)
        os.system("rm -f " + path.join(path_handler.slurm_script_bench_root, "*"))

        if self.benchmark.resources is not None:
            for key, value in self.benchmark.resources.items():
                os.system("cp " +
                          path.join(path_handler.target_systems_root, settings.BENCHMARK["name"], value) + " "
                          + path_handler.slurm_script_bench_root)

        os.makedirs(path_handler.slurm_nfs_bench_root, exist_ok=True)
        os.system("rm -rf " + path.join(path_handler.slurm_nfs_bench_root, "*"))

        os.makedirs(path_handler.slurm_nfs_bench_perf_root, exist_ok=True)
        os.system("rm -f " + path.join(path_handler.slurm_nfs_bench_perf_root, "*"))

    def fetch_and_clean(self):
        self.wait_for_running_jobs(settings.BENCHMARK["name"])

        os.system("rm -f " + path.join(path_handler.slurm_nfs_bench_perf_root, "*"))
        self.__exec_cmd__(["sbatch",
                           path.join(path_handler.slurm_script_bench_root,
                                     settings.BENCHMARK["name"] + "-cleanup-job.sh")])
        print("[Slurm] Submitted cleanup job")

        self.wait_for_running_jobs("cleanup")
        if self.data_collector is not None:
            self.data_collector.collect()

    def wait_for_running_jobs(self, job_name):
        print("[Slurm] Wait for job completion")
        time.sleep(1)
        while self.job_is_running(job_name):
            time.sleep(1)

    def create_job_submission_script(self):
        job_name = settings.BENCHMARK["name"]
        with open(path.join(path_handler.slurm_script_bench_root, job_name + "-run.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            out_file.write("pushd " + path_handler.slurm_script_bench_root + "\n")

            if self.benchmark.resources is not None:
                for key, value in self.benchmark.resources.items():
                    out_file.write("cp " + value + " " + path_handler.slurm_nfs_bench_root + "\n")

            out_file.write("cp -f " + job_name + "-workload-*.sh " + path_handler.slurm_nfs_bench_root + " \n")
            # out_file.write("sleep 1\n")
            out_file.write("cp -f " + job_name + "-cleanup.sh " + path_handler.slurm_nfs_bench_root + " \n\n")
            out_file.write("# <PARALLEL EXECUTION>\n")
            out_file.write("sbatch " + job_name + "-slurm-job.sh\n")
            out_file.write("popd")

    def create_slurm_job_script(self, max_array):
        job_name = settings.BENCHMARK["name"]
        array = "1-" + str(max_array)
        # array = "1-" + str(settings.RUN_REPETITIONS)

        with open(path.join(path_handler.slurm_script_bench_root, job_name + "-slurm-job.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            out_file.write("# <SLURM PARAMETER>\n")
            out_file.write("#SBATCH --job-name=" + job_name + "\n")
            out_file.write("#SBATCH --array=" + array + "\n")
            out_file.write("#SBATCH --partition=" + settings.SLURM_PARTITION + "\n")

            if settings.SLURM_NODE_CONF["exclude"] is not None:
                out_file.write("#SBATCH --exclude=" + settings.SLURM_NODE_CONF["exclude"] + "\n")

            out_file.write("#SBATCH --output=%x-%N-%j.out\n")
            out_file.write("#SBATCH --error=%x-%N-%a.err\n")
            out_file.write("#SBATCH --chdir=/home/" + getpass.getuser() + "/benchmarks/\n\n")

            out_file.write("# <DATA PREPARATION>\n")
            out_file.write("srun mkdir -p " + job_name + "\n")
            out_file.write("cd " + job_name + "\n")

            if self.benchmark.resources is not None:
                for key, value in self.benchmark.resources.items():
                    out_file.write(
                        "srun cp -f " + path.join(path_handler.slurm_nfs_bench_root, value) + " .\n"
                    )

            out_file.write(
                "srun cp -f \"" + path.join(path_handler.slurm_nfs_bench_root,
                                            job_name + "-workload-${SLURM_ARRAY_TASK_ID}.sh") + "\" .\n")
            out_file.write(
                "srun cp -f " + path.join(path_handler.slurm_nfs_bench_root, job_name + "-cleanup.sh") + " .\n\n")

            out_file.write("# <JOB EXECUTION>\n")
            out_file.write("srun /bin/bash \"" + job_name + "-workload-${SLURM_ARRAY_TASK_ID}.sh\"\n\n")

    def create_cleanup_job_script(self):
        job_name = settings.BENCHMARK["name"]
        with open(path.join(path_handler.slurm_script_bench_root, job_name + "-cleanup-job.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            out_file.write("# <SLURM PARAMETER>\n")
            out_file.write("#SBATCH --job-name=cleanup\n")
            out_file.write("#SBATCH --nodelist=" + settings.SLURM_NODE_CONF["include"] + "\n")
            out_file.write("#SBATCH --partition=" + settings.SLURM_PARTITION + "\n")
            out_file.write("#SBATCH --ntasks-per-node=1\n")
            # out_file.write("#SBATCH --output=%x-%N-%j.out\n")
            out_file.write("#SBATCH --error=%x-%N-%j.err\n")
            out_file.write(
                "#SBATCH --chdir=/home/" + getpass.getuser() + "/benchmarks/" + settings.BENCHMARK["name"] + "\n\n")

            # out_file.write("rm " + path.join(path_handler.slurm_nfs_bench_perf_root, "*") + "\n")
            out_file.write("srun /bin/bash " + job_name + "-cleanup.sh")

    def create_cleanup_script(self):
        job_name = settings.BENCHMARK["name"]
        with open(path.join(path_handler.slurm_script_bench_root, job_name + "-cleanup.sh"), "w") as out_file:
            out_file.write("#!/bin/bash\n\n")
            # out_file.write(
            #     "cp -t " + path_handler.slurm_nfs_bench_perf_root + " *.ldjson\n")
            out_file.write(
                "find ../ -not -empty -type f -name \"*.err\" -o -name \"*.ldjson\" | xargs -r cp -t "
                + path_handler.slurm_nfs_bench_perf_root + "\n\n"
            )

            out_file.write(
                "find ../ -type f -name \"*.err\" -o -name \"*.ldjson\" -o -name \"*-workload-*.sh\" -o -name "
                "\"*.out\" | xargs -r rm -f"
            )
            # out_file.write("rm *.ldjson\n")
            # out_file.write("rm *-workload-*.sh\n")
            # out_file.write("rm *.err\n")
            # out_file.write("rm *.out")

    def create_workload_script(self, script_file_path, run):
        timestamp = "date --iso-8601=ns"

        with open(script_file_path, "w") as script_file:
            script_file.write("#!/bin/bash\n\n")
            script_file.write("job_begin=$(" + timestamp + ")\n")
            script_file.write("sleep 1\n\n")

            script_file.write("host=$(hostname)\n")
            script_file.write("outfile=\"${SLURM_JOB_NAME}-${host}-measures.ldjson\"\n\n")

            script_file.write("peak=$(" + timestamp + ")\n")
            script_file.write("stress --cpu 8 --io 4 --vm 4 --vm-bytes 1024 --hdd 4 --timeout 5s\n")
            script_file.write("sleep 10\n\n")

            script_file.write("begin=$(" + timestamp + ")\n")
            script_file.write(self.benchmark.create_exc_cmd(run.sw_config) + "\n")
            script_file.write("end=$(" + timestamp + ")\n\n")

            script_file.write("sleep 10\n")
            script_file.write("job_end=$(" + timestamp + ")\n")
            script_file.write("echo \"{\\\"slurm_job_id\\\":\\\"${SLURM_ARRAY_JOB_ID}\\\", " +
                              "\\\"run_spec_id\\\":\\\"" + str(run.id) + "\\\", " +
                              "\\\"sw_config_id\\\":\\\"" + str(run.sw_config.id) + "\\\", " +
                              "\\\"repetition\\\":\\\"${SLURM_ARRAY_TASK_ID}\\\", " +
                              "\\\"host\\\":\\\"${host}\\\", " +
                              "\\\"command\\\":\\\"" + self.benchmark.create_exc_cmd(run.sw_config) + "\\\", " +
                              "\\\"begin\\\":\\\"${begin}\\\", " +
                              "\\\"end\\\":\\\"${end}\\\", " +
                              "\\\"job_begin\\\":\\\"${job_begin}\\\", " +
                              "\\\"job_end\\\":\\\"${job_end}\\\", " +
                              "\\\"peak\\\":\\\"${peak}\\\"}\" " +
                              "| tee -a \"${outfile}\"\n\n")

        return script_file_path
