from sampling.binary.pair_wise import PairWise
from sampling.binary.feature_wise import FeatureWise
from sampling.binary.all_combinations import AllCombinations
from sampling.numeric.n_random import NRandom
from sampling.numeric.central_normal import CentralNormal

NRANDOM_N = 10

# BINARY_SAMPLER = PairWise()
BINARY_SAMPLER = FeatureWise()
# BINARY_SAMPLER = AllCombinations()

# NUMERIC_SAMPLER = NRandom(NRANDOM_N)
NUMERIC_SAMPLER = CentralNormal()

DATA_DRY_RUN = False
DATA_BUFFER_SIZE = 100

RUN_REPETITIONS = 1
RUN_NODES = 9

BENCHMARK = "locate"
# BENCHMARK = "blender"