import abc


class Environment(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def execute(self, benchmark):
        pass
