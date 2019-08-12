from enum import Enum


class Slurm(Enum):
    PARTITION_TESLA = "tesla"

    # (include, exclude)
    NODES_ALL = {"include": "tesla[001-010]", "exclude": None}
    NODES_COARSE = {"include": "tesla[001,003-010]", "exclude": "tesla002"}
    NODES_FINE = {"include": "tesla002", "exclude": "tesla[001,003-010]"}

