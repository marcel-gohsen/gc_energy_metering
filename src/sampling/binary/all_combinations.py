import itertools

from sampling.sampling_strategy import SamplingStrategy


class AllCombinations(SamplingStrategy):
    def __init__(self, feature_model=None):
        super().__init__(feature_model)

    def sample(self):
        bin_features = self.feature_model.get_binary_features()
        print("[SMPL] Binary sampling on " + str(len(bin_features)) + " features")
        samples = []

        for config in itertools.product([False, True], repeat=len(bin_features)):
            feature_values = {}
            for i in range(len(bin_features)):
                feature_values[bin_features[i]] = config[i]

            samples.append(feature_values)

        return samples
