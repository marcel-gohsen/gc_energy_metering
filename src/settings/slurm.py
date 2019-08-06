from enum import Enum


class Slurm(Enum):
    PARTITION_TESLA = "tesla"

    NODES_ALL = "tesla001,tesla002,tesla003,tesla004,tesla005,tesla006,tesla007,tesla008,tesla009,tesla010"
    NODES_COARSE = "tesla001,tesla003,tesla004,tesla005,tesla006,tesla007,tesla008,tesla009,tesla010"
    NODES_FINE = "tesla002"

