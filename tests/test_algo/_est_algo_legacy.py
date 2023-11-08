import json
import logging

from time import monotonic

import pytest

from algo.models import Algo, AlgoMetric, AlgoSlice
from flow.lib.flow_processor import FlowProcessor
from flow.workflow import CalculateAllAlgoMetricsWorkflow
from task.lib.network_client import NetworkClient
from task.models import TaskState
from tests.test_algo.conftest import algo_scope
from ticker.models import Scope

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


@pytest.fixture
def algo(algo_scope: Scope):
    alg = Algo.objects.create(name='Algo', reference_scope=algo_scope)
    alg.save()
    pe_metric = AlgoMetric.objects.create(
        name='price_earnings',
        algo=alg,
        weight=0.6,
        normalization_method='minmax',
        target_model='FinvizFundamental',
        target_field='price_earnings',
    )
    pe_metric.save()
    ps_metric = AlgoMetric.objects.create(
        name='price_sales',
        algo=alg,
        weight=0.4,
        normalization_method='minmax',
        target_model='FinvizFundamental',
        target_field='price_sales',
    )
    ps_metric.save()
    yield alg


def test_calculate_algo_metrics(
        network_client_on_dispatcher: NetworkClient,
        algo: Algo
):
    flow_processor = FlowProcessor()
    workflow = CalculateAllAlgoMetricsWorkflow()
    flow = workflow.create()
    workflow.arguments_update({'algo_id': algo.id})
    #logger.debug(task.arguments)
    start = monotonic()
    while not flow.processing_state == TaskState.DONE and monotonic() < start + 20:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        flow.refresh_from_db()
        # logger.debug(task.arguments)
    logger.info(monotonic() - start)
    # logger.info(json.dumps(task.result, indent=4))
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
