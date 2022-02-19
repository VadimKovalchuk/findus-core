import logging

from time import sleep
from typing import Union

import pytest

from django.utils.timezone import now

from common.broker import Task
from task.lib.commands import COMMANDS, Command
from task.lib.constants import TaskType
from task.lib.network_client import NetworkClient
from task.models import NetworkTask, TaskState

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


def test_task_queues(network_client_on_dispatcher: NetworkClient):
    client = network_client_on_dispatcher
    created_task = create_network_task(arguments='test')
    pending_task: NetworkTask = next(client.queues[TaskType.Network][TaskState.STARTED])
    assert created_task == pending_task, 'Pending task differs from created one'
    client.push_task_to_network(pending_task)
    assert not next(client.queues[TaskType.Network][TaskState.STARTED]), 'Unexpected network task received'
    pending_task.refresh_from_db()
    assert pending_task.sent, 'Network task is send to DCN but not marked as sent'
    for _ in range(20):  # x100 milliseconds
        sleep(0.1)
        task_result: Task = next(client.queues[TaskType.Network][TaskState.PROCESSED])
        if task_result:
            break
    else:
        raise AssertionError('Task result is not received from network')
    client.append_task_result_to_db(task_result)
    pending_task.refresh_from_db()
    assert pending_task.processed, f'Task result is processed but not marked as processed'
    assert not next(client.queues[TaskType.Network][TaskState.PROCESSED]), 'Unexpected task is received from DCN'


def test_task_forwarding(network_client_on_dispatcher: NetworkClient):
    client = network_client_on_dispatcher
    task = create_network_task(arguments='test')
    client.stage_handler(client.push_task_to_network, TaskState.STARTED)
    sleep(0.1)
    client.stage_handler(client.append_task_result_to_db, TaskState.PROCESSED)
    task.refresh_from_db()
    assert task.processed, f'Task result is processed but not marked as processed'
