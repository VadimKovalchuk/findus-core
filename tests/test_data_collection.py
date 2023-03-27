import json
import logging

from datetime import datetime, timedelta
from time import monotonic, sleep

import pytest

from task.lib.commands import COMMANDS, Command
from task.lib.network_client import NetworkClient
from task.lib.task_processor import TaskProcessor
from task.models import SystemTask, TaskState
from ticker.models import Ticker, Scope, Price

from tests.test_edge import calculate_boundaries
from tests.utils import get_date_by_delta

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def test_ticker_list(network_client_on_dispatcher: NetworkClient):
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['update_ticker_list']
    task: SystemTask = cmd.create_task()
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 20:
        task_proc.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        task.refresh_from_db()
        logger.debug(task.child_stats())
        sleep(0.5)
    logger.info(monotonic() - start)
    children = task.get_children()
    assert children, 'Children tasks are not created'
    for child in children:
        assert child.state == TaskState.DONE, 'Child Network task is not in done state'
    assert task.state == TaskState.DONE, 'System task is not in done state'
    args_ticker_count = len(task.result.split(','))
    db_ticker_count = Ticker.objects.count()
    # logger.debug((args_ticker_count, db_ticker_count))
    _min, _max = calculate_boundaries(args_ticker_count, 0.5)
    assert _min <= db_ticker_count <= _max, f'Ticker count "{args_ticker_count}" ' \
                                            f'in args differs from one from DB "{db_ticker_count}"'
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
    # result = json.loads(task.result)
    # args_price_count = len(result['prices'])
    # db_price_count = ticker_sample.price_set.count()
    # logger.debug((db_price_count, args_price_count))
    # assert db_price_count == args_price_count, \
    #     f'Ticker price count in args "{args_price_count}" differs from one from DB "{db_price_count}"'
    # _min, _max = boundaries
    # assert _min <= db_price_count <= _max, \
    #     f'Tickers price count "{db_price_count}" does not fit expected boundaries({_min},{_max})'


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
