import argparse
import atexit
import json

from data_collector.data_collector import DataCollector
from database.database import Database
from environments.slurm_environment import SlurmEnvironment
from evaluation.plotter import Plotter
from execution.benchmark import Benchmark
from execution.run_specification import RunSpecification
from feature_model.feature_model import FeatureModel
from listeners.pdu_listener import PDUListener
from sampling.sampler import sample_configs
from settings import settings
from train.model_trainer import ModelTrainer
from utility import path_handler


class Launcher:
    def __init__(self, environment=SlurmEnvironment):
        print("[LAUNCH] Initialize")
        self.id_cache = {}

        self.db = Database(args.u, args.p)
        self.data_collector = DataCollector(self.db, dry_run=settings.DATA_DRY_RUN)
        # self.data_collector.add_listener(ArduinoPowerListener())
        self.data_collector.add_listener(PDUListener(sample_rate=2))

        feature_model = FeatureModel(path_handler.model_path)
        self.sampled_configs = sample_configs(feature_model)

        self.benchmark = Benchmark(bench_config_path=path_handler.bench_config_path)

        self.environment = environment(self.data_collector)
        self.evaluator = Plotter(self.db)

        self.model_trainer = ModelTrainer(self.db)

    def launch(self):
        self.sync_with_db()

        if self.data_collector.listeners is not None:
            for listener in self.data_collector.listeners:
                listener.start()

        print("[LAUNCH] Execute benchmark")
        self.environment.execute(self.benchmark)

        if self.data_collector.listeners is not None:
            for listener in self.data_collector.listeners:
                listener.stop()

    def evaluate(self, fixed_data=None):
        if fixed_data is None:
            ids = self.id_cache["run_sched"]
        else:
            ids = fixed_data

        self.evaluator.plot_energy_performance_tradeoff(ids, self.model_trainer.plotted_figures, metric="power")
        self.model_trainer.plotted_figures += 1
        self.evaluator.plot_energy_performance_tradeoff(ids, self.model_trainer.plotted_figures, metric="energy")
        self.model_trainer.plotted_figures += 1
        self.evaluator.plot_performance_by_host(ids,  self.model_trainer.plotted_figures)
        self.model_trainer.plotted_figures += 1
        self.evaluator.plot_config_variance(ids)
        self.model_trainer.plotted_figures += 1

        self.evaluator.plot_power_curve(4451)
        self.model_trainer.plotted_figures += 1
        self.evaluator.plot_power_curve(3807)
        self.model_trainer.plotted_figures += 1

    def train_models(self, fixed_data=None):
        if fixed_data is None:
            ids = self.id_cache["run_sched"]
        else:
            ids = fixed_data

        self.model_trainer.train(ids, settings.BENCHMARK["name"])

    def sync_with_db(self):
        print("[LAUNCH] Sync with DB")
        hw_conf_id = 1  # TODO: Read from file or something
        self.id_cache["hw_conf"] = hw_conf_id

        self.id_cache["sw_system"] = self.db.request_id(
            "system_sw", "name", self.benchmark.command_name, [self.benchmark.command_name])

        bench_cmd = self.benchmark.command_name + " [OPTIONS] " + " ".join(self.benchmark.arguments)
        self.id_cache["benchmark"] = self.db.request_id("benchmark", "command", bench_cmd,
                                                        [settings.BENCHMARK["name"], bench_cmd])
        self.benchmark.id = self.id_cache["benchmark"]

        for config in self.sampled_configs:
            feature_hash = config.compute_hash()
            bin_features = config.get_binary_features()
            num_features = config.get_numeric_features()

            config.id = self.db.request_id("conf_sw", "feature_hash", feature_hash,
                                           [feature_hash, json.dumps(bin_features), json.dumps(num_features)])

            run_id = self.db.request_id("run_spec",
                                        ["hw_conf", "sw_system", "sw_version", "sw_conf", "benchmark"],
                                        [self.id_cache["hw_conf"], self.id_cache["sw_system"], 0, config.id,
                                         self.benchmark.id],
                                        [self.id_cache["hw_conf"], self.id_cache["sw_system"], 0, config.id,
                                         self.benchmark.id])

            self.benchmark.add_run(
                RunSpecification(run_id, config, hw_conf_id)
            )

        sched_id = self.db.get_free_index("run_schedule")
        self.id_cache["run_sched"] = [x for x in
                                      range(sched_id, sched_id + settings.RUN_REPETITIONS * len(self.benchmark.runs))]

    def shutdown(self):
        print("[LAUNCH] Shutdown...")
        self.db.close()


def main():
    launcher = Launcher(SlurmEnvironment)
    fixed_data = None

    # fixed_data = [x for x in range(21, 683 + 1)]
    # fixed_data = [x for x in range(698, 748 + 1)]
    # fixed_data = [x for x in range(3802, 4521 + 1)]

    if fixed_data is None:
        launcher.launch()

    launcher.train_models(fixed_data)
    launcher.evaluate(fixed_data)

    atexit.register(launcher.shutdown)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", metavar="db_user", type=str, required=True, help="user name to connect to the db server")
    parser.add_argument("-p", metavar="db_password", type=str, required=True, help="associated password to connect to "
                                                                                   "the db server")

    args = parser.parse_args()

    main()
