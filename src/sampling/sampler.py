import itertools

from config.config import Config
from settings import settings


class Sampler:
    def __init__(self, feature_model, binary_strategy, numeric_strategy):
        self.feature_model = feature_model

        self.binary_sampler = binary_strategy
        self.numeric_sampler = numeric_strategy

    def sample(self):
        print("[SMPL] Start sampling")
        bin_configs = self.binary_sampler.sample()
        num_configs = self.numeric_sampler.sample()
        configs = []

        if len(num_configs) > 0:
            for bin_num_comb in itertools.product(bin_configs, num_configs):
                conf_merge = {**bin_num_comb[0], **bin_num_comb[1]}

                current = Config(self.feature_model.features, conf_merge)

                if self.feature_model.is_valid(current):
                    configs.append(current)
        elif len(bin_configs) > 0:
            for bin_config in bin_configs:
                current = Config(self.feature_model.features, bin_config)

                if self.feature_model.is_valid(current):
                    configs.append(current)

        print("[SMPL] Sampled " + str(len(configs)) + " configs")

        return configs


def sample_configs(feature_model):
    bin_sampling = settings.BINARY_SAMPLER.set_feature_model(feature_model)
    num_sampling = settings.NUMERIC_SAMPLER.set_feature_model(feature_model)

    sampler = Sampler(feature_model, bin_sampling, num_sampling)
    return sampler.sample()
