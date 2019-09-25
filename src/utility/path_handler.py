import getpass
import os.path as path

from settings import settings

project_dir = path.abspath(path.join(path.dirname(__file__), "..", ".."))
resources_root = path.join(project_dir, "resources")
data_root = path.join(project_dir, "data")
buffer_root = path.join(data_root, "buffer")
target_systems_root = path.join(resources_root, "target-systems")
plot_root = path.join(data_root, "plots")
model_root = path.join(data_root, "models")

model_path = path.join(target_systems_root, settings.BENCHMARK["model-path"])
bench_config_path = path.join(target_systems_root, settings.BENCHMARK["config-path"])

slurm_script_root = path.join(data_root, "slurm")
slurm_script_bench_root = path.join(slurm_script_root, settings.BENCHMARK["name"])

slurm_nfs_root = path.join("/media/raid/", getpass.getuser())
slurm_nfs_bench_root = path.join(slurm_nfs_root, settings.BENCHMARK["name"])
slurm_nfs_bench_perf_root = path.join(slurm_nfs_bench_root, "performance")
