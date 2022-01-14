import json
import logging

from copy import deepcopy
from time import sleep

import pytest

from client.client import Client
from common.constants import SECOND
from common.data_structures import compose_queue, task_body
from common.defaults import RoutingKeys

logger = logging.getLogger(__name__)

task_input_queue = compose_queue(RoutingKeys.TASK)
task_result_queue = compose_queue(RoutingKeys.RESULTS)


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


@pytest.mark.parametrize('module_func', [
    'get_sp500_ticker_list',
    'get_sp400_ticker_list',
    'get_sp600_ticker_list'
])
def test_ticker_list(client_on_dispatcher: Client, module_func):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'findus-edge.tickers'
    test_task['function'] = module_func
    client.broker.push(test_task)
    # Validating result on client
    result = False
    while not result:
        try:
            result = next(client.broker.pulling_generator())
        except StopIteration:
            logger.debug('Waiting for Agent reply')
    client.broker.set_task_done(result)
    logger.info(len(json.loads(result.body['result'])))
