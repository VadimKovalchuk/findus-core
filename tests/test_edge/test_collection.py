import json
import logging

from copy import deepcopy
from datetime import datetime, timedelta
from time import sleep
from typing import Union, Tuple

import pytest

from dcn.client.client import Client
from dcn.common.data_structures import compose_queue, task_body
from dcn.common.defaults import RoutingKeys

logger = logging.getLogger(__name__)

task_input_queue = compose_queue(RoutingKeys.TASK)
task_result_queue = compose_queue(RoutingKeys.RESULTS)


def calculate_boundaries(expected: Union[int, float], accuracy: float) -> Tuple[float, float]:
    _min = expected * (100 - accuracy) / 100
    _max = expected * (100 + accuracy) / 100
    return _min, _max


def test_availability(client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.stub'
    test_task['arguments'] = {"test_arg_1": "test_val_1",
                              "test_arg_2": "test_val_2"}
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    assert test_task['arguments'] == result['result'], \
        'Wrong task is received from task queue for Agent'


@pytest.mark.parametrize('scope, expected', [
    pytest.param('SP500', 500, id='sp500'),
    pytest.param('SP400', 400, id='sp400'),
    pytest.param('SP600', 600, id='sp600')
])
def test_ticker_list(
        client_on_dispatcher: Client,
        scope: str,
        expected: int
):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.tickers'
    test_task['function'] = 'get_scope'
    test_task['arguments'] = {"scope": scope}
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    ticker_count = len(json.loads(result['result']))
    logger.info(f'Tickers count: {ticker_count}')
    _min, _max = calculate_boundaries(expected, 1.2)
    assert _min <= ticker_count <= _max, \
        f'Tickers count "{ticker_count}" does not fit expected boundaries({_min},{_max})'


def test_price_history(client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.yahoo'
    test_task['function'] = 'ticker_history'
    today = datetime.today()
    start_date = today - timedelta(weeks=13)  # 3 month ago
    test_task['arguments'] = {'ticker': 'MSFT', 'start': start_date.strftime('%Y-%m-%d')}
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    data = json.loads(result['result'])
    price_count = len(data['prices'])
    dividend_count = len(data['dividends'])
    logger.info(f'Price rows: {price_count}, Dividend rows: {dividend_count}')
    _min, _max = calculate_boundaries(62, 5)
    assert _min <= price_count <= _max, f'Price count does not fit expected boundaries({_min},{_max})'
    assert dividend_count, 'Dividend rows are missing'


@pytest.mark.parametrize('module_func, expected_prop_count', [
    pytest.param('fundamental', 78, id='fundamental'),
    pytest.param('fundamental_converted', 40, id='fundamental_converted')
])
def test_finviz_fundamental_collection(client_on_dispatcher: Client, module_func: str, expected_prop_count: int):
    ticker = 'MSFT'
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.finviz'
    test_task['function'] = module_func
    test_task['arguments'] = {'ticker': ticker}
    #test_task['arguments'] = '{"ticker": "MSFT"}'
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    logger.debug(result)
    data = json.loads(result['result'])
    assert 'values' in data, f'Ticker fundamental values are missing in command result contents'
    assert len(data['values']) == expected_prop_count, \
        f'Fields count differs in fundamental data for ticker {ticker}: ' \
        f'actual - {len(data["values"])}, expected - {expected_prop_count}'
