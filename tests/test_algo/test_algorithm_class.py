import logging
import pytest

from algo.algorithm import get_algorithm_map
from algo.algorithm.test import TestAlgorithm
from algo.models import Algo, AlgoMetric


logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def test_algorithm_deploy():
    ref_algorithm = TestAlgorithm()
    ref_algorithm.deploy()
    algo: Algo = ref_algorithm.algo
    algorithm_map = get_algorithm_map()
    assert algo.name in algorithm_map, f'Algo {algo.name} is missing in algorithm map: {algorithm_map.keys()}'
    result_algorithm = algorithm_map.get(algo.name)
    assert result_algorithm == TestAlgorithm, 'Result class does not corresponds to reference one'
    algorithm = result_algorithm(algo)
    algorithm.validate_db_correspondence()
