import json
import logging

from time import monotonic

import pytest

from algo.algorithm.test import TestAlgorithm
from algo.algorithm.generic import Algorithm
from algo.models import Algo, AlgoMetric, AlgoSlice
from flow.lib.flow_processor import FlowProcessor
from flow.workflow import CalculateAlgoMetricsWorkflow
from task.lib.network_client import NetworkClient
from task.models import TaskState
from tests.test_algo.conftest import algo_scope
from ticker.models import Scope

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


@pytest.fixture
def algorithm(algo_scope: Scope) -> Algorithm:
    algorithm = TestAlgorithm()
    algorithm.scope = algo_scope
    algorithm.deploy()
    yield algorithm


def test_calculate_algo_metrics(
        network_client_on_dispatcher: NetworkClient,
        algorithm: Algorithm,
):
    flow_processor = FlowProcessor()
    algo = algorithm.algo
    workflow = CalculateAlgoMetricsWorkflow()
    flow = workflow.create()
    workflow.arguments_update({'algo_name': algo.name, 'is_reference': True})
    start = monotonic()
    while not flow.processing_state == TaskState.DONE and monotonic() < start + 20:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        flow.refresh_from_db()
        # logger.debug(task.arguments)
    logger.info(monotonic() - start)
    for metric in algo.metrics:
        parameters = metric.method_parameters_dict
        logger.debug(json.dumps(parameters, indent=4))
        values = metric.get_normalization_data().values()
        assert 'min' in parameters, "MIN value is missing in parameters"
        assert parameters["min"] == min(values), f"Metric MIN value {parameters['min']} " \
                                                 f"differs from expected: {min(values)}"
        assert 'max' in parameters, "MAX value is missing in parameters"
        assert parameters["max"] == max(values), f"Metric MAX value {parameters['max']} " \
                                                 f"differs from expected: {max(values)}"
    for ticker in algo.reference_scope.tickers.all():
        algo_slices = list(algo.get_slices_by_ticker(ticker))
        assert len(algo_slices) == 1, f"Single slice is expected for ticker {ticker}"
        algo_slice: AlgoSlice = algo_slices[0]
        assert len(algo_slice.metrics) == 2, f"Slice for ticker {ticker} has metrics count mismatch"
