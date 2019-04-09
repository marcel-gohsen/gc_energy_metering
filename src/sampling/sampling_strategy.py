import abc


class SamplingStrategy(metaclass=abc.ABCMeta):
    def __init__(self, feature_model=None):
        self.feature_model = None

        if feature_model is not None:
            self.set_feature_model(feature_model)

    @abc.abstractmethod
    def sample(self):
        pass

    def set_feature_model(self, feature_model):
        self.feature_model = feature_model

        return self
