import json
import logging

from datetime import datetime, timedelta
from time import monotonic, sleep

import pytest

from flow.lib.flow_processor import FlowProcessor
from flow.workflow import ScopeUpdateWorklow
from task.lib.commands import COMMANDS, Command
from task.lib.network_client import NetworkClient
from task.models import SystemTask, TaskState
from ticker.models import Ticker, Scope, Price

from tests.test_edge.test_collection import calculate_boundaries
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
    workflow = ScopeUpdateWorklow()
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
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['append_daily_ticker_data']
    task: SystemTask = cmd.create_task()
    task.arguments = json.dumps({'ticker': ticker_sample.symbol, 'start': start_date})
    task.save()
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 20:
        task_proc.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        task.refresh_from_db()
    logger.info(monotonic() - start)
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
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['collect_daily_global']
    task: SystemTask = cmd.create_task()
    set_sample_prices()
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 20:
        task_proc.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        task.refresh_from_db()
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
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['append_finviz_fundamental']
    task: SystemTask = cmd.create_task()
    task.arguments = json.dumps({"ticker": ticker_sample.symbol})
    task.save()
    logger.debug(task.arguments)
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 20:
        task_proc.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        task.refresh_from_db()
    logger.info(monotonic() - start)
    result = json.loads(task.result)
    data_slice_count = ticker_sample.finvizfundamental_set.count()
    assert data_slice_count == 1, 'Ticker fundamental data was not correctly appended'
    data_slice = ticker_sample.finvizfundamental_set.all()[0]
    for param, value in result['values'].items():
        assert getattr(data_slice, param) == value, f'Param "{param}" value mismatch "{getattr(data_slice, param)}" vs "{value}"'


def test_finviz_fundamental_global(
        network_client_on_dispatcher: NetworkClient,
        scope_with_tickers: Scope,
):
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['collect_finviz_fundamental_global']
    task: SystemTask = cmd.create_task()
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 20:
        task_proc.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        task.refresh_from_db()
    logger.info(monotonic() - start)
    for ticker in scope_with_tickers.tickers.all():
        db_finviz_count = ticker.finvizfundamental_set.count()
        logger.info(f'{ticker.symbol} fundamental slice count: {db_finviz_count}')
        assert db_finviz_count == 1, f'Tickers finviz fundamental slice count "{db_finviz_count}" is not 1'
