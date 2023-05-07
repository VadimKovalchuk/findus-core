import json
import logging

from time import monotonic

import pytest

from algo.models import Algo, AlgoMetric, AlgoSlice, AlgoMetricSlice
from task.lib.commands import COMMANDS, Command
from task.lib.network_client import NetworkClient
from task.lib.task_processor import TaskProcessor
from task.models import SystemTask, TaskState
from ticker.models import Scope, Ticker, FinvizFundamental
from tests.test_edge.test_normalization import UNIFORM_DISTRIBUTION_DATA

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


@pytest.fixture
def algo_scope():
    scope = Scope.objects.create(name='scope')
    for symbol in UNIFORM_DISTRIBUTION_DATA:
        tkr = Ticker.objects.create(symbol=symbol)
        tkr.save()
        scope.tickers.add(tkr)
        finviz_slice = FinvizFundamental.objects.create(
            ticker=tkr,
            price_earnings=UNIFORM_DISTRIBUTION_DATA[symbol],
            price_sales=UNIFORM_DISTRIBUTION_DATA[symbol] * 2
        )
        finviz_slice.save()
    scope.save()
    yield scope


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
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['calculate_algo_metrics']
    task: SystemTask = cmd.create_task()
    args = task.arguments_dict
    args['algo_id'] = algo.id
    task.arguments_dict = args
    task.save()
    logger.debug(task.arguments)
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 20:
        task_proc.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        task.refresh_from_db()
        # logger.debug(task.arguments)
    logger.info(monotonic() - start)
    result = json.loads(task.result)
    logger.info(json.dumps(result, indent=4))
    # data_slice_count = ticker_sample.finvizfundamental_set.count()
    # assert data_slice_count == 1, 'Ticker fundamental data was not correctly appended'
    # data_slice = ticker_sample.finvizfundamental_set.all()[0]
    # for param, value in result['values'].items():
    #     assert getattr(data_slice, param) == value, f'Param "{param}" value mismatch "{getattr(data_slice, param)}" vs "{value}"'

