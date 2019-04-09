class NumericRange:
    def __init__(self, min, max, step=None):
        self.min = min
        self.max = max
        self.step = step

    def __contains__(self, item):
        if item < self.min:
            return False
        elif item > self.max:
            return False

        if self.is_integer():
            if isinstance(item, float):
                if not item.is_integer():
                    return False

        return True

    def __len__(self):
        return int(self.max - self.min) + 1

    def __str__(self):
        return "{} - {}".format(self.min, self.max)

    def __repr__(self):
        return self.__str__()

    def is_integer(self):
        if self.step is None:
            return False

        return self.step.is_integer()
