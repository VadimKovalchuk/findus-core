import logging

import pytest

from django.utils.timezone import now

from task.lib.commands import COMMANDS, Command
from task.lib.constants import TaskType
from task.lib.network_client import NetworkClient
from task.lib.task_processor import TaskProcessor
from task.models import Task, SystemTask, NetworkTask, TaskState
from ticker.models import Ticker

from tests.test_edge import calculate_boundaries

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


REFERENCE_TICKER = 'MSFT'
DAILY_TEST_DATA = [
    ["2022-06-24", 261.81, 267.98, 261.72, 267.7, 33900700.0],
    ["2022-06-27", 268.21, 268.3, 263.28, 264.89, 24600800.0],
    ["2022-06-28", 263.98, 266.91, 258.14, 259.08, 11307292.0]
]
DIVIDEND_TEST_DATA = [
        ["2021-05-19", 0.56],
        ["2021-08-18", 0.56],
        ["2021-11-17", 0.62],
        ["2022-02-16", 0.62],
        ["2022-05-18", 0.62]
    ]


@pytest.fixture()
def ticker_sample():
    ticker = Ticker(symbol=REFERENCE_TICKER)
    ticker.save()
    yield ticker


def test_ticker_price_append(ticker_sample: Ticker):
    for price in DAILY_TEST_DATA:
        ticker_sample.add_price(price)
    assert ticker_sample.price_set.count() == len(DAILY_TEST_DATA), \
        'Price count mismatch for sample ticket. ' \
        f'Expected: {len(DAILY_TEST_DATA)}, actual: {ticker_sample.price_set.count()}'


def test_ticker_dividend_append(ticker_sample: Ticker):
    for dividend in DIVIDEND_TEST_DATA:
        ticker_sample.add_dividend(dividend)
    assert ticker_sample.dividend_set.count() == len(DIVIDEND_TEST_DATA), \
        'Dividend count mismatch for sample ticket. ' \
        f'Expected: {len(DIVIDEND_TEST_DATA)}, actual: {ticker_sample.dividend_set.count()}'
