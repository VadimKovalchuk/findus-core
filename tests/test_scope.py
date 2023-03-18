import logging
from time import monotonic

import pytest

from ticker.models import Ticker, Scope
from task.models import Task, SystemTask, NetworkTask, TaskState
from task.lib.commands import COMMANDS, Command
from task.lib.task_processor import TaskProcessor


logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db

TEST_TICKERS_STR_LIST = ['MSFT', 'C', 'T', 'META']
TEST_SCOPE_NAME = 'TestScope'

@pytest.fixture
def scope_tickers():
    tickers = list()
    for ticker_str in TEST_TICKERS_STR_LIST:
        tkr = Ticker.objects.create(symbol=ticker_str)
        tkr.save()
        tickers.append(tkr)
    yield tickers


@pytest.fixture
def scope():
    test_scope = Scope.objects.create(name=TEST_SCOPE_NAME)
    test_scope.save()
    yield test_scope


@pytest.fixture
def scope_with_tickers(scope, scope_tickers):
    for ticker in scope_tickers:
        scope.tickers.add(ticker)
    scope.save()
    yield scope


def test_scope_extend_direct(scope_with_tickers, scope_tickers):
    for ticker in scope_tickers:
        assert ticker in scope_with_tickers.tickers.all(), f'{ticker} is missing in scope'
    for ticker in scope_with_tickers.tickers.all():
        assert ticker in scope_tickers, f'Redundant {ticker} is detected in scope'


def test_scope_remove_direct(scope_with_tickers, scope_tickers):
    removed_ticker = scope_tickers[0]
    logger.info(f'Removing ticker: {removed_ticker}')
    scope_with_tickers.tickers.remove(removed_ticker)
    scope_with_tickers.save()
    assert removed_ticker not in scope_with_tickers.tickers.all(), 'Ticker remains in scope when not expected'


def _test_scope_extend_via_task(scope_with_tickers):
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS[SYS_CMD_NAME]
    task: SystemTask = cmd.create_task()
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 5:
        task_proc.processing_cycle()
        task.refresh_from_db()
    logger.info(monotonic() - start)
    children = task.get_children()
    assert children, 'Children tasks are not created'
    for child in children:
        assert child.state == TaskState.DONE, 'Child Network task is not in done state'
    assert task.state == TaskState.DONE, 'System task is not in done state'

