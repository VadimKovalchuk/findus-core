import json
import logging
from time import monotonic

import pytest

from tests.conftest import TEST_TICKERS_STR_LIST
from ticker.models import Ticker, Scope
from task.models import Task, TaskState
from flow.lib.flow_processor import FlowProcessor
from flow.workflow import TestScopeWorklow


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
    flow_processor = FlowProcessor()
    workflow = TestScopeWorklow()
    flow = workflow.create()
    for _ in range(2):
        flow_processor.processing_cycle()
    child_task: Task = flow.tasks[0]
    assert child_task, 'Children task is not created'
    child_task.result_dict = [artifact_tkr] + TEST_TICKERS_STR_LIST
    child_task.state = TaskState.PROCESSED
    child_task.save()
    for _ in range(2):
        flow_processor.processing_cycle()
    tickers_str = [tkr.symbol for tkr in scope_with_tickers.tickers.all()]
    assert artifact_tkr in tickers_str, 'Artifact ticker is missing in scope'
    assert len(tickers_str) == len(TEST_TICKERS_STR_LIST) + 1, 'Scope ticker count does not match'


def test_scope_reduce_via_task(scope_with_tickers):
    flow_processor = FlowProcessor()
    workflow = TestScopeWorklow()
    flow = workflow.create()
    for _ in range(2):
        flow_processor.processing_cycle()
    child_task: Task = flow.tasks[0]
    assert child_task, 'Children task is not created'
    child_task.result_dict = TEST_TICKERS_STR_LIST[1:]
    child_task.state = TaskState.PROCESSED
    child_task.save()
    for _ in range(2):
        flow_processor.processing_cycle()
    tickers_str = [tkr.symbol for tkr in scope_with_tickers.tickers.all()]
    assert TEST_TICKERS_STR_LIST[0] not in tickers_str, 'Artifact ticker is missing in scope'
    assert len(tickers_str) == len(TEST_TICKERS_STR_LIST) - 1, 'Scope ticker count does not match'
