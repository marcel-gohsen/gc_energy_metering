import itertools

from sampling.sampling_strategy import SamplingStrategy


class FeatureWise(SamplingStrategy):
    def __init__(self, feature_model=None):
        super().__init__(feature_model)

    def sample(self):
        bin_features = self.feature_model.get_binary_features()
        print("[SMPL] Binary sampling on " + str(len(bin_features)) + " features")
        samples = []

        for i in range(len(bin_features)):
            conf = [False] * len(bin_features)

            conf[i] = True

            feature_values = dict(zip(bin_features, conf))
            feature_values = self.feature_model.make_binary_valid(feature_values)

            samples.append(feature_values)
            samples = [x[0] for x in itertools.groupby(samples)]

        return samples
