import itertools
import statistics

from sampling.sampling_strategy import SamplingStrategy


class CentralComposite(SamplingStrategy):
    def __init__(self, feature_model=None):
        super().__init__(feature_model)

    def sample(self):
        num_features = self.feature_model.get_numeric_features()
        samples = []

        print("[SMPL] Numeric sampling on " + str(len(num_features)) + " features")
        feature_values = {}
        for feature in num_features:
            feature_values[feature] = []
            feature_range = self.feature_model.numeric_ranges[feature]

            feature_values[feature].append(float(feature_range.min))
            feature_values[feature].append(float(feature_range.max))
            feature_values[feature].append(float(
                statistics.median(
                    range(int(feature_range.min), int(feature_range.max)))))

        for config in itertools.product(*feature_values.values()):
            samples.append(dict(zip(feature_values.keys(), config)))

        return samples
