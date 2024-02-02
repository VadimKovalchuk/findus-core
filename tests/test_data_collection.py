import json
import logging

from datetime import datetime, timedelta
from time import monotonic, sleep

import pytest

from flow.lib.flow_processor import FlowProcessor
from flow.models import FlowState
from flow.workflow import (ScopeUpdateWorkflow, AddAllTickerPricesWorkflow, AppendTickerPricesWorfklow,
                           AppendFinvizWorkflow, AddAllTickerFinvizWorkflow)
from task.lib.network_client import NetworkClient
from task.models import Task, TaskState
from ticker.models import Ticker, Scope, Price

from tests.tests_edge.test_collection import calculate_boundaries
from tests.utils import get_date_by_delta

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


@pytest.fixture
def sp_scopes():
    tkr = Ticker.objects.create(symbol='X')
    tkr.save()
    for scope_name in ["SP500", "SP400", "SP600"]:
        test_scope = Scope.objects.create(name=scope_name)
        logger.debug(f"Creating scope: {scope_name}")
        test_scope.tickers.add(tkr)
        test_scope.save()


def test_ticker_list(network_client_on_dispatcher: NetworkClient, sp_scopes):
    flow_processor = FlowProcessor()
    workflow = ScopeUpdateWorkflow()
    flow = workflow.create()
    start = monotonic()
    while not flow.processing_state == TaskState.DONE and monotonic() < start + 60:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        flow.refresh_from_db()
        logger.debug([task.state for task in flow.tasks])
        sleep(0.5)
    logger.info(monotonic() - start)
    for task in flow.tasks:
        assert task.processing_state == TaskState.DONE, 'Task is not in done state'
    assert flow.processing_state == TaskState.DONE, 'Flow is not in done state'
    db_ticker_count = Ticker.objects.count()
    _min, _max = calculate_boundaries(1500, 0.5)
    assert _min <= db_ticker_count <= _max, \
        f'Tickers count "{db_ticker_count}" does not fit expected boundaries({_min},{_max})'


@pytest.mark.parametrize("start_date, boundaries", [
    # pytest.param(HISTORY_LIMIT_DATE, (1380, 1480), id='full_history'),
    pytest.param(get_date_by_delta(timedelta(weeks=13)), (60, 65), id='three_month_gap'),
    pytest.param(get_date_by_delta(timedelta(days=2)), (1, 3), id='daily'),
])
def test_ticker_daily_data(
        network_client_on_dispatcher: NetworkClient,
        ticker_sample: Ticker,
        start_date: str,
        boundaries: tuple
):
    flow_processor = FlowProcessor()
    workflow = AppendTickerPricesWorfklow()
    workflow.create()
    workflow.arguments = {'ticker': ticker_sample.symbol}
    workflow.set_for_test()
    flow_processor.processing_cycle()
    workflow.refresh_from_db()
    task = workflow.tasks[0]
    task.update_arguments({'start': start_date})
    start = monotonic()
    while not workflow.processing_state == FlowState.DONE and monotonic() < start + 5:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        workflow.refresh_from_db()
        sleep(0.1)
    logger.info(monotonic() - start)
    task.refresh_from_db()
    result = json.loads(task.result)
    args_price_count = len(result['prices'])
    db_price_count = ticker_sample.price_set.count()
    logger.debug((db_price_count, args_price_count))
    assert db_price_count == args_price_count, \
        f'Ticker price count in args "{args_price_count}" differs from one from DB "{db_price_count}"'
    _min, _max = boundaries
    assert _min <= db_price_count <= _max, \
        f'Tickers price count "{db_price_count}" does not fit expected boundaries({_min},{_max})'


def test_daily_global(
        network_client_on_dispatcher: NetworkClient,
        scope_with_tickers: Scope,
):
    def set_sample_prices():
        last_date: datetime = get_date_by_delta(timedelta(weeks=13))
        for ticker in scope_with_tickers.tickers.all():
            ticker.add_price([last_date, 1, 1, 1, 1, 1])

    _min, _max = 60, 65
    flow_processor = FlowProcessor()
    workflow = AddAllTickerPricesWorkflow()
    workflow.create()
    workflow.set_for_test()
    set_sample_prices()
    start = monotonic()
    while not workflow.processing_state == FlowState.DONE and monotonic() < start + 5:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        workflow.refresh_from_db()
        sleep(0.1)
        #logger.info([wf.state for wf in workflow.child_flows])
    logger.info(monotonic() - start)
    for ticker in scope_with_tickers.tickers.all():
        db_price_count = ticker.price_set.count()
        logger.info(f'{ticker.symbol} price count: {db_price_count}')
        assert _min <= db_price_count <= _max, \
            f'Tickers price count "{db_price_count}" does not fit expected boundaries({_min},{_max})'


def test_finviz_fundamental(
        network_client_on_dispatcher: NetworkClient,
        ticker_sample: Ticker
):
    flow_processor = FlowProcessor()
    workflow = AppendFinvizWorkflow()
    workflow.create()
    workflow.arguments = {'ticker': ticker_sample.symbol}
    workflow.set_for_test()
    start = monotonic()
    while not workflow.processing_state == TaskState.DONE and monotonic() < start + 5:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        workflow.refresh_from_db()
        sleep(0.1)
    logger.info(monotonic() - start)
    result = json.loads(workflow.tasks[0].result)
    data_slice_count = ticker_sample.finvizfundamental_set.count()
    assert data_slice_count == 1, 'Ticker fundamental data was not correctly appended'
    data_slice = ticker_sample.finvizfundamental_set.all()[0]
    for param, value in result['values'].items():
        assert getattr(data_slice, param) == value, f'Param "{param}" value mismatch "{getattr(data_slice, param)}" vs "{value}"'


def test_finviz_fundamental_global(
        network_client_on_dispatcher: NetworkClient,
        scope_with_tickers: Scope,
):
    flow_processor = FlowProcessor()
    workflow = AddAllTickerFinvizWorkflow()
    workflow.create()
    workflow.set_for_test()
    start = monotonic()
    while not workflow.processing_state == TaskState.DONE and monotonic() < start + 5:
        flow_processor.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        workflow.refresh_from_db()
        sleep(0.1)
    logger.info(monotonic() - start)
    for ticker in scope_with_tickers.tickers.all():
        db_finviz_count = ticker.finvizfundamental_set.count()
        logger.info(f'{ticker.symbol} fundamental slice count: {db_finviz_count}')
        assert db_finviz_count == 1, f'Tickers finviz fundamental slice count "{db_finviz_count}" is not 1'
