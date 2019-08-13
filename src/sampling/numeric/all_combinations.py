import itertools

from sampling.sampling_strategy import SamplingStrategy


class AllCombinations(SamplingStrategy):
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

            for i in range(int(feature_range.min), int(feature_range.max) + 1, int(feature_range.step)):
                feature_values[feature].append(float(i))

        for config in itertools.product(*feature_values.values()):
            samples.append(dict(zip(feature_values.keys(), config)))

        return samples
