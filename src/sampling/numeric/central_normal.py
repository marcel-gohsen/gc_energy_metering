from sampling.sampling_strategy import SamplingStrategy

import statistics
import math
import numpy as np
import random
import itertools
import matplotlib.pyplot as plt

from feature_model.feature_model import FeatureModel


class CentralNormal(SamplingStrategy):
    def __init__(self, n=None, means=None, scale=0.05, feature_model=None):
        super().__init__(feature_model)

        self.num_means = means
        self.scale = scale
        self.n = n

    def sample(self):
        num_features = self.feature_model.get_numeric_features()
        print("[SMPL] Numeric sampling on " + str(len(num_features)) + " features")

        if len(num_features) == 0:
            return []

        samples = []
        feature_values = {}

        for feature in num_features:
            feature_range = self.feature_model.numeric_ranges[feature]

            mean_locs = set()

            if feature_range.is_integer():
                if self.num_means is None:
                    num_means = int(math.log10(len(feature_range)))

                    if num_means == 0:
                        num_means = 1
                    self.i_split(feature_range.min, feature_range.max, num_means, mean_locs)
                else:
                    self.i_split(feature_range.min, feature_range.max, self.num_means, mean_locs)

                mean_locs.add(int(feature_range.min))
                mean_locs.add(int(feature_range.max))

                feature_values[feature] = []
                if self.n is None:
                    self.n = 3

                for _ in range(self.n):
                    mean_loc = random.choice([*mean_locs])
                    if self.scale is None:
                        value = int(np.random.normal(mean_loc,  2 * int(math.log2(len(feature_range)))))
                    else:
                        value = int(np.random.normal(mean_loc, self.scale))

                    if value in feature_range:
                        feature_values[feature].append(value)
                    else:
                        feature_values[feature].append(mean_loc)

            # self.plot_distribution(feature_values[feature], mean_locs, feature_range)

        value_vectors = []
        feature_index = {}

        i = 0
        for key, value in feature_values.items():
            value_vectors.append(value)
            feature_index[key] = i
            i += 1

        for value_vector in itertools.product(*value_vectors):
            sample = {}
            for key, value in feature_index.items():
                sample[key] = float(value_vector[value])
            samples.append(sample)

        return samples

    @staticmethod
    def plot_distribution(feature_values, mean_locs, feature_range):
        plt.plot([*mean_locs], [0] * len(mean_locs), "o", color="black", label="Medians")
        plt.hist(feature_values, bins=[int(x) for x in range(int(feature_range.min), int(feature_range.max + 1))],
                 color="#8bc34a", alpha=0.75)
        # plt.ylim(feature_range.max)
        plt.xlabel("Sampled value")
        plt.ylabel("Number of samples")
        # plt.title("Sampling with Median Normal",)
        plt.grid(True)
        plt.axis([feature_range.min, feature_range.max, 0, len(feature_values) / (len(feature_range) * 0.3)])
        plt.legend()
        plt.savefig("../../../data/plots/median_normal_" + str(feature_range.min) + "-" + str(feature_range.max) + ".png", transparent=True, dpi=200)
        # plt.show()

    def i_split(self, min, max, num_means, mean_locs):
        if num_means == 0:
            return

        median = statistics.median_low([x for x in range(int(min), int(max) + 1)])
        mean_locs.add(median)

        self.i_split(min, median, num_means - 1, mean_locs)
        self.i_split(median, max, num_means - 1, mean_locs)


if __name__ == '__main__':
    sampler = CentralNormal(n=3, means=1, scale=0, feature_model=FeatureModel("../../../resources/target-systems/blender/blender.xml"))
    print(sampler.sample())
