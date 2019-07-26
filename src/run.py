import argparse
import atexit
import copy
import json
import os.path as path

from settings import settings
from sampling.sampler import sample_configs
from utility import path_handler
from data_collector.data_collector import DataCollector
from database.database import Database
from environments.slurm_environment import SlurmEnvironment
from evaluation.plotter import Plotter
from execution.benchmark import Benchmark
from execution.run_specification import RunSpecification
from feature_model.feature_model import FeatureModel
from listeners.arduino_power_listener import ArduinoPowerListener
from train.model_trainer import ModelTrainer


class Launcher:
    def __init__(self, bench_descriptor, environment=SlurmEnvironment):
        print("[LAUNCH] Initialize")
        self.id_cache = {}

        # self.db = Database(args.u, args.p)
        # self.data_collector = DataCollector(self.db, dry_run=settings.DATA_DRY_RUN)
        # self.data_collector.add_listener(ArduinoPowerListener())

        feature_model = FeatureModel(path_handler.model_path)
        self.sampled_configs = sample_configs(feature_model)

        self.benchmark = Benchmark(path_handler.bench_config_path)

        self.runs = []

        # self.environment = environment(self.data_collector)
        self.environment = environment()
        # self.evaluator = Plotter(self.db)
        #
        # self.model_trainer = ModelTrainer(self.db)

    def launch(self):
        self.sync_with_db(self.benchmark.command_name)

        if self.data_collector.listeners is not None:
            for listener in self.data_collector.listeners:
                listener.start()

        print("[LAUNCH] Execute benchmark")
        self.environment.execute(self.runs, buffer_size=setup.DATA_BUFFER_SIZE)

        if self.data_collector.listeners is not None:
            for listener in self.data_collector.listeners:
                listener.stop()

    def evaluate(self, fixed_data=None):
        if fixed_data is None:
            ids = self.id_cache["run_sched"]
        else:
            ids = fixed_data

        self.evaluator.plot_energy_performance_tradeoff(ids, self.benchmark.name, self.model_trainer.plotted_figures)
        self.model_trainer.plotted_figures += 1
        self.evaluator.plot_performance_by_host(ids, self.benchmark.name, self.model_trainer.plotted_figures)
        self.model_trainer.plotted_figures += 1

    def train_models(self, fixed_data=None):
        if fixed_data is None:
            ids = self.id_cache["run_sched"]
        else:
            ids = fixed_data

        self.model_trainer.train(ids, self.benchmark.name)

    def sync_with_db(self, ts):
        print("[LAUNCH] Sync with DB")
        hw_conf_id = 1  # TODO: Read from file or something
        self.id_cache["hw_conf"] = hw_conf_id

        if self.db.contains_value("system_sw", "name", ts):
            ts_id = self.db.get_indices_of("system_sw", "name", ts)[0]
        else:
            ts_id = self.db.get_free_index("system_sw")
            self.db.insert_data("system_sw", [ts_id, ts])

        self.id_cache["sw_system"] = ts_id

        bench_cmd = self.benchmark.command_name + " [OPTIONS] " + " ".join(self.benchmark.arguments)

        if self.db.contains_value("benchmark", "command", bench_cmd):
            bench_id = self.db.get_indices_of("benchmark", "command", bench_cmd)[0]
        else:
            # bench_id = self.db.get_free_index("benchmark")
            bench_id = self.db.insert_data("benchmark",
                                           [self.benchmark.name, bench_cmd], fields=["name", "command"])

        self.id_cache["benchmark"] = bench_id
        self.benchmark.id = bench_id

        for config in self.sampled_configs:
            feature_vector = tuple([config.feature_values[x] for x in sorted(config.features)])

            feature_hash = hash(feature_vector)

            bin_features = {x: config.feature_values[x] for x in config.features if
                            config.features[x] == "abstract" or config.features[x] == "binary"}

            num_features = {x: config.feature_values[x] for x in config.features if
                            config.features[x] == "numeric"}

            if self.db.contains_value("conf_sw", "feature_hash", feature_hash):
                sw_conf_id = self.db.get_indices_of("conf_sw", "feature_hash", feature_hash)[0]
            else:
                sw_conf_id = self.db.get_free_index("conf_sw")
                self.db.insert_data("conf_sw",
                                    [sw_conf_id, feature_hash, json.dumps(bin_features), json.dumps(num_features)])

            config.id = sw_conf_id

            run_id = self.db.get_indices_of("run_spec", ["hw_conf", "sw_system", "sw_version", "sw_conf", "benchmark"],
                                            [hw_conf_id, ts_id, 0, sw_conf_id, bench_id])

            if len(run_id) == 0:
                run_id = self.db.get_free_index("run_spec")
                self.db.insert_data("run_spec", [run_id, hw_conf_id, ts_id, 0, sw_conf_id, bench_id])
            else:
                run_id = run_id[0]

            self.runs.append(
                RunSpecification(run_id, self.benchmark, config, hw_conf_id,
                                 repetitions=setup.RUN_REPETITIONS,
                                 nodes=setup.RUN_NODES))

            # if len(self.runs) == 2:
            #     break

        sched_id_start = self.db.get_free_index("run_schedule")
        num_sched_ids = 0

        for run in self.runs:
            num_sched_ids += run.repetitions * run.nodes

        self.id_cache["run_sched"] = [x for x in range(sched_id_start, sched_id_start + num_sched_ids)]
        self.data_collector.sched_id_pool = copy.deepcopy(self.id_cache["run_sched"])

    def shutdown(self):
        print("[LAUNCH] Shutdown...")
        self.db.close()


def main():
    launcher = Launcher(settings.BENCHMARK, SlurmEnvironment)
    # fixed_data = [x for x in range(245565, 245654 + 1)]
    # fixed_data = [x for x in range(246567, 247556 + 1)]
    # fixed_data = [x for x in range(250527, 261326 + 1)]
    # fixed_data = [x for x in range(261867, 262046 + 1)]
    # fixed_data = [x for x in range(263279, 265704 + 1)]

    # fixed_data = None
    #
    # if fixed_data is None:
    #     launcher.launch()
    #
    # launcher.train_models(fixed_data)
    # launcher.evaluate(fixed_data)

    # atexit.register(launcher.shutdown)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", metavar="db_user", type=str, required=True, help="user name to connect to the db server")
    parser.add_argument("-p", metavar="db_password", type=str, required=True, help="associated password to connect to "
                                                                                   "the db server")

    args = parser.parse_args()

    main()
