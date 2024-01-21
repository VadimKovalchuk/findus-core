import logging

from datetime import timedelta
from time import sleep
from typing import Union

import pytest

from django.utils.timezone import now

from task.lib.network_client import NetworkClient
from task.models import Task, TaskState

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def create_task(module: str = 'findus_edge.stub', function: str = 'relay', arguments: dict = {}):
    task: Task = Task.objects.create(name='pytest')
    task.module = module
    task.function = function
    task.arguments_dict = arguments
    task.state = TaskState.CREATED
    task.save()
    logger.debug(f'Network task is created: {task}')
    return task


def pull_task(queue, strict=True):
    for _ in range(20):  # x20 milliseconds
        sleep(0.1)
        task_result = next(queue)
        if task_result:
            return task_result
    else:
        if strict:
            raise AssertionError('Task result is not received from network')


def test_db_mixin_integration(network_client: NetworkClient):
    assert network_client.db_connected, f'Database connection failure'


def test_online(network_client_on_dispatcher: NetworkClient):
    assert network_client_on_dispatcher.online, f'Network client has not reached online state'


def test_task_queues(network_client_on_dispatcher: NetworkClient):
    client = network_client_on_dispatcher
    created_task = create_task(arguments={"arg": "test"})
    pending_task: Task = next(client.queues[TaskState.CREATED])
    assert created_task == pending_task, 'Pending task differs from created one'
    client.push_task_to_network(pending_task)
    assert not next(client.queues[TaskState.CREATED]), 'Unexpected network task received'
    pending_task.refresh_from_db()
    assert pending_task.sent, 'Network task is send to DCN but not marked as sent'
    task_result = pull_task(client.queues[TaskState.PROCESSED])
    client.append_task_result_to_db(task_result)
    pending_task.refresh_from_db()
    assert pending_task.state == TaskState.PROCESSED, f'Task result is processed but not marked as processed'
    assert not next(client.queues[TaskState.PROCESSED]), 'Unexpected task is received from DCN'


def test_task_forwarding(network_client_on_dispatcher: NetworkClient):
    client = network_client_on_dispatcher
    task = create_task(arguments={"arg": "test"})
    client.generic_stage_handler(client.push_task_to_network, TaskState.CREATED)
    task.refresh_from_db()
    logger.debug(task.state)
    client.generic_stage_handler(client.append_task_result_to_db, TaskState.PROCESSED)
    task.refresh_from_db()
    logger.debug(task.state)
    assert task.state == TaskState.PROCESSED, f'Task result is processed but not marked as processed'


@pytest.mark.parametrize('target_state', [
    pytest.param(TaskState.CREATED),
    pytest.param(TaskState.STARTED),
])
def test_task_postpone_cycle(network_client_on_dispatcher: NetworkClient, target_state: str):
    client = network_client_on_dispatcher
    task = create_task(arguments={"arg": "test"})
    task.processing_state = target_state
    if target_state == TaskState.STARTED:
        task.sent = now()
    task.postponed = now() + timedelta(hours=1)
    task.save()
    task_result = pull_task(client.queues[TaskState.POSTPONED], strict=False)
    assert not task_result, 'Unexpired postponed task is postponed queue'
    task_result = pull_task(client.queues[target_state], strict=False)
    assert not task_result, f'Task is detected in {target_state} queue, when not expected'
    client.processing_cycle()
    task.refresh_from_db()
    logger.debug(task.state)
    assert task.state == TaskState.POSTPONED, 'Task exited postponed state when not expected'
    task.postponed = now() - timedelta(hours=1)
    task.save()
    client.processing_cycle()
    task.refresh_from_db()
    logger.debug(task.state)
    assert task.state != TaskState.POSTPONED, 'Task did not exited postponed state when expected'
    task_result = pull_task(client.queues[TaskState.POSTPONED], strict=False)
    assert not task_result, 'Unpostponed task remains in postponed queue'
    task_result = pull_task(client.queues[target_state])
    assert task_result, f'Task is not detected in {target_state} queue, when expected'


def test_task_failure_detection(network_client_on_dispatcher: NetworkClient):
    client = network_client_on_dispatcher
    task = create_task(function='negative', arguments={"arg": "test"})
    client.processing_cycle()
    sleep(0.1)
    task_result = pull_task(client._pull_task_result())
    logger.debug(task_result)

