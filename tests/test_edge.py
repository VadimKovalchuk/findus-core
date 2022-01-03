import logging

from copy import deepcopy
from time import sleep

from client.client import Client
from common.data_structures import compose_queue, task_body
from common.defaults import RoutingKeys

logger = logging.getLogger(__name__)

task_input_queue = compose_queue(RoutingKeys.TASK)
task_result_queue = compose_queue(RoutingKeys.RESULTS)


def test_availability(client_on_dispatcher: Client):
    client = client_on_dispatcher
    # Send task from client
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.input_queue
    test_task['module'] = 'stub'
    test_task['arguments'] = {'test_arg_1': 'test_val_1',
                              'test_arg_2': 'test_val_2'}
    client.broker.push(test_task)
    sleep(1)
    # Validating result on client
    result = next(client.broker.pulling_generator())
    client.broker.set_task_done(result)
    assert test_task['arguments'] == result['result'], \
        'Wrong task is received from task queue for Agent'
