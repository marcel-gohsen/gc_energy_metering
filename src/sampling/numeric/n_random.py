import random
import itertools

from sampling.sampling_strategy import SamplingStrategy


class NRandom(SamplingStrategy):
    def __init__(self, n, feature_model=None):
        super().__init__(feature_model)
        self.n = n

    def sample(self):
        num_features = self.feature_model.get_numeric_features()
        print("[SMPL] Numeric sampling on " + str(len(num_features)) + " features")

        if len(num_features) == 0:
            return []

        samples = []

        while len(samples) != self.n:
            feature_values = {}
            for feature in num_features:
                num_range = self.feature_model.numeric_ranges[feature]

                if num_range.is_integer():
                    rand = float(random.randint(num_range.min, num_range.max))

                    if rand in num_range:
                        feature_values[feature] = rand

            if len(feature_values) > 0:
                samples.append(feature_values)
                samples = [x[0] for x in itertools.groupby(samples)]

        print(samples)
        return samples
