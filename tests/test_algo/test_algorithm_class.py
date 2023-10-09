from algo.algorithm.test import TestAlgorithm
from algo.models import Algo, AlgoMetric


def test_algorithm_deploy():
    algorithm = TestAlgorithm()
    algo = algorithm.deploy()
