import logging

from time import sleep
from typing import Union

import pytest

from django.utils.timezone import now

from common.broker import Task
from task.lib.commands import COMMANDS, Command
from task.lib.network_client import NetworkClient
from task.models import NetworkTask

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def create_network_task(module: str = 'findus-edge.stub', function: str = 'relay', arguments: Union[str, None] = None):
    task: NetworkTask = NetworkTask.objects.create(name='pytest')
    task.module = module
    task.function = function
    task.arguments = arguments
    task.started = now()
    task.save()
    logger.debug(f'Network task is created: {task}')
    return task


def test_db_mixin_integration(network_client: NetworkClient):
    assert network_client.db_connected, f'Database connection failure'


def test_online(network_client_on_dispatcher: NetworkClient):
    assert network_client_on_dispatcher.online, f'Network client has not reached online state'


def test_task_forwarding(network_client_on_dispatcher: NetworkClient):
    client = network_client_on_dispatcher
    created_task = create_network_task(arguments='test')
    pending_task: NetworkTask = next(client.pending_tasks)
    assert created_task == pending_task, 'Pending task differs from created one'
    client.push_task_to_network(pending_task)
    assert not next(client.pending_tasks), 'Unexpected network task received'
    pending_task.refresh_from_db()
    assert pending_task.started, 'Network task is send to DCN but not marked as started'
    for _ in range(20):  # x100 milliseconds
        task_result: Task = next(client.task_results)
        if task_result:
            break
    else:
        raise AssertionError('Task result is not received from network')
    client.append_task_result_to_db(task_result)
    pending_task.refresh_from_db()
    assert pending_task.processed, f'Task result is processed but not marked as processed'


def test_commands_interaction(network_client_on_dispatcher: NetworkClient):
    client = network_client_on_dispatcher
    command = COMMANDS['network_relay_task']
    created_task: NetworkTask = command.create_task()
    command.on_start(created_task)
    created_task.arguments = 'test'
    created_task.started = now()
    created_task.save()
    pending_task: NetworkTask = next(client.pending_tasks)
    client.push_task_to_network(pending_task)
    for _ in range(20):  # x100 milliseconds
        task_result: Task = next(client.task_results)
        if task_result:
            logger.debug(f'DCN reply is received after {_}00ms')
            break
    else:
        raise AssertionError('Task result is not received from network')
    client.append_task_result_to_db(task_result)
    created_task.refresh_from_db()
    command.finalize(created_task)
    assert created_task.result == 'test, relay, relay', 'Task result differs from expected value'
