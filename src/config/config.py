class Config:
    def __init__(self, features, feature_values):
        self.features = features
        self.feature_values = feature_values

        self.id = -1

    def compute_hash(self):
        feature_vector = tuple([self.feature_values[x] for x in sorted(self.features)])

        return hash(feature_vector)

    def get_binary_features(self):
        return {x: self.feature_values[x] for x in self.features if
                self.features[x] == "abstract" or self.features[x] == "binary"}

    def get_numeric_features(self):
        return {x: self.feature_values[x] for x in self.features if
                self.features[x] == "numeric"}
