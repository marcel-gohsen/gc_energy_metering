import xml.etree.ElementTree as ET

from error_handling.error_handler import ErrorHandler
from config.config import Config


class ConfigParser:
    def __init__(self, feature_model_path, configs_path):
        try:
            self.feature_file = open(feature_model_path, "r")
        except IOError as err:
            ErrorHandler.handle("C-Parser", "Error open feature model " + feature_model_path, err)

        try:
            self.configs_file = open(configs_path)
        except IOError as err:
            ErrorHandler.handle("C-Parser", "Error open configs file " + feature_model_path, err)

    def parse(self):
        configs = []
        features = {}

        doc_tree = ET.parse(self.feature_file)
        doc_root = doc_tree.getroot()

        for child in doc_root.find("binaryOptions"):
            feature = child.find("name").text.replace("_", "-")

            features[feature] = "binary"

            if child.find("prefix").text == "abstract":
                features[feature] = "abstract"

        for child in doc_root.find("numericOptions"):
            feature = child.find("name").text.replace("_", "-")
            features[feature] = "numeric"

        header = True
        options = []

        for line in self.configs_file:
            feature_values = {}

            if header:
                header = False
                options = line.replace("\n", "").split(";")
                options = list(map(lambda x: x.replace("_", "-"), options))
            else:
                values = line.replace("\n", "").split(";")

                for i in range(len(options)):
                    if features[options[i]] == "binary" or features[options[i]] == "abstract":
                        feature_values[options[i]] = (values[i] == "1")
                    elif features[options[i]] == "numeric":
                        feature_values[options[i]] = float(values[i])

                configs.append(Config(features, feature_values))

        return configs
