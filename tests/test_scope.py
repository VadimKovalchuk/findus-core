import json
import logging
from time import monotonic

import pytest

from tests.conftest import TEST_TICKERS_STR_LIST
from ticker.models import Ticker, Scope
from task.models import Task, SystemTask, NetworkTask, TaskState
from task.lib.commands import COMMANDS, Command
# from task.lib.task_processor import TaskProcessor


logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


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


def test_scope_extend_via_task(scope_with_tickers):
    artifact_tkr = "AMZN"
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['update_test_scopes']
    task: SystemTask = cmd.create_task()
    for _ in range(2):
        task_proc.processing_cycle()
    children: NetworkTask = task.get_children()[0]
    assert children, 'Children task is not created'
    children.result_dict = [artifact_tkr] + TEST_TICKERS_STR_LIST
    children.state = TaskState.PROCESSED
    children.save()
    for _ in range(2):
        task_proc.processing_cycle()
    tickers_str = [tkr.symbol for tkr in scope_with_tickers.tickers.all()]
    assert artifact_tkr in tickers_str, 'Artifact ticker is missing in scope'
    assert len(tickers_str) == len(TEST_TICKERS_STR_LIST) + 1, 'Scope ticker count does not match'


def test_scope_reduce_via_task(scope_with_tickers):
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS['update_test_scopes']
    task: SystemTask = cmd.create_task()
    for _ in range(2):
        task_proc.processing_cycle()
    children: NetworkTask = task.get_children()[0]
    assert children, 'Children task is not created'
    children.result_dict = TEST_TICKERS_STR_LIST[1:]
    children.state = TaskState.PROCESSED
    children.save()
    for _ in range(2):
        task_proc.processing_cycle()
    tickers_str = [tkr.symbol for tkr in scope_with_tickers.tickers.all()]
    assert TEST_TICKERS_STR_LIST[0] not in tickers_str, 'Artifact ticker is missing in scope'
    assert len(tickers_str) == len(TEST_TICKERS_STR_LIST) - 1, 'Scope ticker count does not match'
