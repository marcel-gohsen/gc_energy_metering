from sampling.binary.pair_wise import PairWise
from sampling.binary.feature_wise import FeatureWise
from sampling.binary.all_combinations import AllCombinations
from sampling.numeric.all_combinations import AllCombinations as NAllCombinations
from sampling.numeric.n_random import NRandom
from sampling.numeric.central_normal import CentralNormal
from sampling.numeric.central_composite import CentralComposite
from settings.slurm import Slurm

NRANDOM_N = 10

# BINARY_SAMPLER = PairWise()
# BINARY_SAMPLER = FeatureWise()
BINARY_SAMPLER = AllCombinations()

# NUMERIC_SAMPLER = NRandom(NRANDOM_N)
# NUMERIC_SAMPLER = CentralNormal(n=3, means=1, scale=0)
# NUMERIC_SAMPLER = NAllCombinations()
NUMERIC_SAMPLER = CentralComposite()

DATA_DRY_RUN = False
DATA_BUFFER_TIME = 5 * 60  # seconds

SLURM_PARTITION = Slurm.PARTITION_TESLA.value
SLURM_NODE_CONF = Slurm.NODES_COARSE.value

RUN_REPETITIONS = 5

# Paths are given relative to target-systems folder in resources
# BENCHMARK = {"name": "locate", "model-path": "locate/locate.xml", "config-path": "locate/locate_bench_config.json"}
BENCHMARK = {"name": "blender", "model-path": "blender/blender.xml", "config-path": "blender/blender_bench_config.json"}

DB_HOST = "intelli001.medien.uni-weimar.de"
DB_NAME = "green_configurator"
