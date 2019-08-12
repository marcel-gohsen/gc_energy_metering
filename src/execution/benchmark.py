import json

from error_handling.error_handler import ErrorHandler
from utility import path_handler
import os.path as path


class Benchmark:
    def __init__(self, bench_config_path):
        self.__parse_config(bench_config_path)
        self.runs = []

    def __parse_config(self, bench_config_path):
        with open(bench_config_path) as conf_file:
            bench_conf = json.load(conf_file)

            self.command_name = bench_conf["command"]

            self.arguments = bench_conf["arguments"]

            self.resources = bench_conf["resources"]
            self.pattern = bench_conf["pattern"]
            self.mappings = bench_conf["mappings"]
            self.single_hyphen = bench_conf["single-hyphen"]
            self.explicit_binary = bench_conf["explicit-binary"]

            self.id = None

        return self

    def create_exc_cmd(self, config):
        command = self.command_name

        if self.pattern is None:
            for feature, feature_type in config.features.items():
                if feature_type == "binary":
                    if config.feature_values[feature]:
                        command += " --" + feature

                if feature_type == "numeric":
                    command += " --" + feature + " " + str(config.feature_values[feature])

            for argument in self.arguments:
                command += " " + argument
        else:
            command = ""
            for item in self.pattern:
                if item in self.arguments:
                    command += " " + self.arguments[item]
                elif item in self.resources:
                    command += " " + self.resources[item]

                elif item in config.features:
                    delim = "--"
                    if self.single_hyphen is not None:
                        if item in self.single_hyphen:
                            delim = "-"

                    if config.features[item] == "binary":
                        if config.feature_values[item]:
                            command += " " + delim + item

                        if self.explicit_binary is not None:
                            if item in self.explicit_binary:
                                if not config.feature_values[item]:
                                    command += " " + delim + item

                                command += " " + str(int(config.feature_values[item]))
                    elif config.features[item] == "numeric":
                        value = config.feature_values[item]

                        if item in self.mappings:
                            value = self.mappings[item][str(int(value))]

                        if isinstance(value, float):
                            if value.is_integer():
                                value = int(value)

                        command += " " + delim + item + " " + str(value)

                else:
                    command += item

        return command

    def add_run(self, run):
        self.runs.append(run)
