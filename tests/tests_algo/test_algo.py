import json
import logging

from time import monotonic, sleep
from typing import List

import pytest

from algo.algorithm.test import TestAlgorithm
from algo.algorithm.generic import Algorithm
from algo.models import Algo, AlgoMetric, AlgoSlice
from flow.lib.flow_processor import FlowProcessor
from flow.workflow import CalculateAlgoMetricsWorkflow, ApplyAlgoMetricsWorkflow, RateAlgoSliceWorkflow, RateAllSlicesWorkflow
from task.lib.network_client import NetworkClient
from task.models import TaskState
from tests.tests_algo.conftest import algo_scope
from ticker.models import Scope, Ticker

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


@pytest.fixture
def algorithm(algo_scope: Scope) -> Algorithm:
    algorithm = TestAlgorithm()
    algorithm.scope = algo_scope
    algorithm.deploy()
    yield algorithm


@pytest.fixture
def algo_with_calculated_metrics(
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
        sleep(1)
    logger.info(monotonic() - start)
    yield algorithm


@pytest.fixture
def cleanup_algo_slices(algorithm: Algorithm):
    algo = algorithm.algo
    for algo_slice in algo.algoslice_set.all():
        algo_slice.delete()
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


def test_apply_metrics(
        network_client_on_dispatcher: NetworkClient,
        algo_with_calculated_metrics: Algorithm,
        cleanup_algo_slices,
):
    flow_processor = FlowProcessor()
    algo = algo_with_calculated_metrics.algo
    flows = []
    for ticker in algo_with_calculated_metrics.scope.tickers.all():
        workflow = ApplyAlgoMetricsWorkflow()
        flow = workflow.create()
        flows.append(flow)
        workflow.arguments_update({'algo_name': algo.name, 'is_reference': True, 'ticker': ticker.symbol})
    start = monotonic()
    while [flow for flow in flows if not flow.processing_state == TaskState.DONE] and monotonic() < start + 10:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        [flow.refresh_from_db() for flow in flows]
    logger.info(monotonic() - start)
    for ticker in algo_with_calculated_metrics.scope.tickers.all():
        slice: AlgoSlice = algo.get_slices_by_ticker(ticker)[0]
        assert len(slice.metrics) == 2, f'Invalid metric slice count'


def test_per_slice_algo_rate(
        network_client_on_dispatcher: NetworkClient,
        algo_with_calculated_metrics: Algorithm,
):
    flow_processor = FlowProcessor()
    algo: Algo = algo_with_calculated_metrics.algo
    flows = []
    for ticker in algo_with_calculated_metrics.scope.tickers.all():
        logger.info(f'Processing ticker: {ticker.symbol}')
        workflow = RateAlgoSliceWorkflow()
        flow = workflow.create()
        flows.append(flow)
        algo_slice = AlgoSlice.objects.get(ticker=ticker)
        workflow.arguments_update({'algo_slice_id': algo_slice.id})
        start = monotonic()
    while [flow for flow in flows if not flow.processing_state == TaskState.DONE] and monotonic() < start + 10:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        [flow.refresh_from_db() for flow in flows]
    logger.info(monotonic() - start)
    algo.refresh_from_db()
    algo_slices: List[AlgoSlice] = algo.algoslice_set.all()
    for algo_slice in algo_slices:
        logger.info(algo_slice)
        assert float(algo_slice.ticker.symbol) / 10 == algo_slice.result, f'Actual rate differs from expected'


def test_bulk_algo_rate(
        network_client_on_dispatcher: NetworkClient,
        algo_with_calculated_metrics: Algorithm,
):
    flow_processor = FlowProcessor()
    algo: Algo = algo_with_calculated_metrics.algo
    workflow = RateAllSlicesWorkflow()
    flow = workflow.create()
    workflow.arguments_update({'algo_name': algo.name})
    start = monotonic()
    while not flow.processing_state == TaskState.DONE and monotonic() < start + 10:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        flow.refresh_from_db()
    logger.info(monotonic() - start)
    algo.refresh_from_db()
    algo_slices: List[AlgoSlice] = algo.algoslice_set.all()
    for algo_slice in algo_slices:
        logger.info(algo_slice)
        assert float(algo_slice.ticker.symbol) / 10 == algo_slice.result, f'Actual rate differs from expected'
