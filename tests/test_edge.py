import json
import logging

from copy import deepcopy
from datetime import datetime, timedelta
from time import sleep
from typing import Union, Tuple

import pytest

from client.client import Client
from common.constants import SECOND
from common.data_structures import compose_queue, task_body
from common.defaults import RoutingKeys

logger = logging.getLogger(__name__)

task_input_queue = compose_queue(RoutingKeys.TASK)
task_result_queue = compose_queue(RoutingKeys.RESULTS)


def calculate_boundaries(expected: Union[int, float], accuracy: int) -> Tuple[float, float]:
    _min = expected * (100 - accuracy) / 100
    _max = expected * (100 + accuracy) / 100
    return _min, _max


def test_availability(client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'findus-edge.stub'
    test_task['arguments'] = {"test_arg_1": "test_val_1",
                              "test_arg_2": "test_val_2"}
    client.broker.push(test_task)
    # Validating result on client
    result = next(client.broker.pulling_generator())
    client.broker.set_task_done(result)
    assert test_task['arguments'] == result.body['result'], \
        'Wrong task is received from task queue for Agent'


@pytest.mark.parametrize('module_func, expected', [
    pytest.param('get_sp500_ticker_list', 500, id='sp500'),
    pytest.param('get_sp400_ticker_list', 400, id='sp400'),
    pytest.param('get_sp600_ticker_list', 600, id='sp600')
])
def test_ticker_list(
        client_on_dispatcher: Client,
        module_func: str,
        expected: int
):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'findus-edge.tickers'
    test_task['function'] = module_func
    client.broker.push(test_task)
    # Validating result on client
    result = next(client.broker.pulling_generator())
    client.broker.set_task_done(result)
    ticker_count = len(json.loads(result.body['result']))
    logger.info(f'Tickers count: {ticker_count}')
    _min, _max = calculate_boundaries(expected, 1)
    assert _min <= ticker_count <= _max, f'Tickers count does not fit expected boundaries({_min},{_max})'


def test_price_history(client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'findus-edge.yahoo'
    test_task['function'] = 'ticker_history'
    today = datetime.today()
    start_date = today - timedelta(weeks=13)  # 3 month ago
    test_task['arguments'] = {'ticker': 'MSFT', 'start': start_date.strftime('%Y-%m-%d')}
    client.broker.push(test_task)
    # Validating result on client
    result = next(client.broker.pulling_generator())
    client.broker.set_task_done(result)
    data = json.loads(result.body['result'])
    price_count = len(data['prices'])
    dividend_count = len(data['dividends'])
    logger.info(f'Price rows: {price_count}, Dividend rows: {dividend_count}')
    _min, _max = calculate_boundaries(62, 5)
    assert _min <= price_count <= _max, f'Price count does not fit expected boundaries({_min},{_max})'
    assert dividend_count, 'Dividend rows are missing'


def test_fundamental(client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'findus-edge.finviz'
    test_task['function'] = 'fundamental'
    ticker_list = ['MSFT', 'GOOGL', 'AAPL', 'AMZN']
    test_task['arguments'] = ticker_list
    client.broker.push(test_task)
    # Validating result on client
    result = next(client.broker.pulling_generator())
    client.broker.set_task_done(result)
    data = json.loads(result.body['result'])
    for ticker in ticker_list:
        assert ticker in data, f'Ticker "{ticker}" is missing in fundamental data contents'
        assert len(data[ticker]) == 77, f'Some fields are missing in fundamental data for ticker {ticker}'
