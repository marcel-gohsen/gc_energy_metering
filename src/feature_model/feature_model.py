import xml.etree.ElementTree as ET

from error_handling.error_handler import ErrorHandler
from feature_model.numeric_range import NumericRange


class FeatureModel:

    def __init__(self, model_path):
        print("[FM] Parse feature model " + model_path)
        self.features = {}
        self.implied_options = {}
        self.excluded_options = {}
        self.mandatory_options = []

        self.numeric_ranges = {}

        try:
            with open(model_path, "r") as model_file:
                doc_tree = ET.parse(model_file)
                doc_root = doc_tree.getroot()

                self.name = doc_root.get("name")

                if self.name is None:
                    raise IOError

                for child in doc_root.find("binaryOptions"):
                    feature = child.find("name").text.replace("_", "-")

                    self.features[feature] = "binary"

                    if child.find("prefix").text == "abstract":
                        self.features[feature] = "abstract"

                    self.__extract_implied_options(feature, child)
                    self.__extract_excluded_options(feature, child)

                    if child.find("optional").text == "False":
                        self.mandatory_options.append(feature)

                for child in doc_root.find("numericOptions"):
                    feature = child.find("name").text.replace("_", "-")
                    self.features[feature] = "numeric"

                    self.__extract_implied_options(feature, child)
                    self.__extract_excluded_options(feature, child)

                    range_min = float(child.find("minValue").text)
                    range_max = float(child.find("maxValue").text)
                    step = float(child.find("stepFunction").text.split(" + ")[1])

                    self.numeric_ranges[feature] = NumericRange(range_min, range_max, step)

        except IOError as err:
            ErrorHandler.handle("F-Model", "Error parsing feature model " + model_path, err)

    def __extract_implied_options(self, feature, element):
        if element.find("impliedOptions").find("options") is None:
            return

        for option in element.find("impliedOptions").find("options").iter():
            if feature not in self.implied_options:
                self.implied_options[feature] = []

            self.implied_options[feature].append(option.text.replace("_", "-"))

    def __extract_excluded_options(self, feature, element):
        if element.find("excludedOptions").find("options") is None:
            return

        for option in element.find("excludedOptions").find("options").iter():
            if feature not in self.excluded_options:
                self.excluded_options[feature] = []

            self.excluded_options[feature].append(option.text.replace("_", "-"))

    def is_valid(self, config):
        for feature, value in config.feature_values.items():
            # Feature does not exist in model
            if feature not in self.features:
                return False

            # Validate binary features
            if self.features[feature] == "binary" or self.features[feature] == "abstract":
                # Feature type is not bool
                if not isinstance(value, bool):
                    return False

                if value:
                    # Check if implied features are turned on
                    if feature in self.implied_options:
                        for option in self.implied_options[feature]:
                            option = option.split(" | ")

                            bin_options = [x for x in option if
                                           self.features[x] == "binary" or self.features[x] == "abstract"]
                            num_options = [x for x in option if self.features[x] == "numeric"]

                            if not any(opt in config.feature_values for opt in num_options) and \
                                    not any(opt in config.feature_values and config.feature_values[opt] for opt in
                                            bin_options):
                                return False

                    # Check if excluded features are turned off
                    if feature in self.excluded_options:
                        for option in self.excluded_options[feature]:
                            if option in config.feature_values:
                                if self.features[option] == "binary" or self.features[option] == "abstract":
                                    if config.feature_values[option]:
                                        return False
                                else:
                                    return False

            # Validate numeric features
            elif self.features[feature] == "numeric":
                # Feature type is not float
                if not isinstance(value, float):
                    return False

                if value not in self.numeric_ranges[feature]:
                    return False

                # Check if implied features are turned on
                if feature in self.implied_options:
                    for option in self.implied_options[feature]:
                        option = option.split(" | ")

                        bin_options = [x for x in option if
                                       self.features[x] == "binary" or self.features[x] == "abstract"]
                        num_options = [x for x in option if self.features[x] == "numeric"]

                        if not any(opt in config.feature_values for opt in num_options) and \
                                not any(
                                    opt in config.feature_values and config.feature_values[opt] for opt in bin_options):
                            return False

                # Check if excluded features are turned off
                if feature in self.excluded_options:
                    for option in self.excluded_options[feature]:
                        if option in config.feature_values:
                            if self.features[option] == "binary" or self.features[option] == "abstract":
                                if config.feature_values[option]:
                                    return False
                            else:
                                return False

        # Check if mandatory features are turned on
        for feature in self.mandatory_options:
            if self.features[feature] == "binary" or self.features[feature] == "abstract":
                if feature in config.feature_values:
                    if not config.feature_values[feature]:
                        return False
            else:
                if feature not in config.feature_values:
                    return False

        return True

    def make_binary_valid(self, bin_conf):
        for feature, value in bin_conf.items():
            if value:
                if feature in self.implied_options:
                    for option in self.implied_options[feature]:
                        bin_conf[option.split(" | ")[0]] = True

                if feature in self.excluded_options:
                    for option in self.excluded_options[feature]:
                        bin_conf[option] = False

        for feature in self.mandatory_options:
            bin_conf[feature] = True

        return bin_conf

    def get_binary_features(self):
        return [x[0] for x in self.features.items() if x[1] == "binary" or x[1] == "abstract"]

    def get_numeric_features(self):
        return [x[0] for x in self.features.items() if x[1] == "numeric"]
