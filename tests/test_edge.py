import json
import logging

from copy import deepcopy
from time import sleep

from client.client import Client
from common.constants import SECOND
from common.data_structures import compose_queue, task_body
from common.defaults import RoutingKeys

logger = logging.getLogger(__name__)

task_input_queue = compose_queue(RoutingKeys.TASK)
task_result_queue = compose_queue(RoutingKeys.RESULTS)


def test_availability(dcn_network, client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'findus-edge.stub'
    test_task['arguments'] = {"test_arg_1": "test_val_1",
                              "test_arg_2": "test_val_2"}
    client.broker.push(test_task)
    client.broker._inactivity_timeout = 1 * SECOND
    # Validating result on client
    result = next(client.broker.pulling_generator())
    client.broker.set_task_done(result)
    assert test_task['arguments'] == result.body['result'], \
        'Wrong task is received from task queue for Agent'


def test_sp500_list(dcn_network, client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'findus-edge.tickers'
    test_task['function'] = 'get_sp500_ticker_list'
    client.broker.push(test_task)
    client.broker._inactivity_timeout = 10 * SECOND
    # Validating result on client
    result = next(client.broker.pulling_generator())
    client.broker.set_task_done(result)
    logger.info(len(json.loads(result.body['result'])))
