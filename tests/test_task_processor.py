import logging

from datetime import timedelta
from time import sleep
from typing import Generator, Union

import pytest

from django.utils.timezone import now

from common.broker import Task
from task.lib.commands import COMMANDS, Command
from task.lib.network_client import NetworkClient
from task.lib.task_processor import TaskProcessor
from task.models import TaskState, Task, SystemTask, NetworkTask

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db

SYS_CMD_NAME = 'system_relay_task'
NET_CMD_NAME = 'network_relay_task'


def validate_task_queue(task: Task, expected_queue: Generator, task_proc: TaskProcessor):
    queues = {'net_' + queue_name: queue for queue_name, queue in task_proc.queues[NetworkTask.__name__].items()}
    queues.update({'sys_' + queue_name: queue for queue_name, queue in task_proc.queues[SystemTask.__name__].items()})
    for queue_name, queue in queues.items():
        received_task = next(queue)
        if queue == expected_queue:
            assert received_task == task, \
                f'Task with state "{task.state}" is missing in corresponding queue: {queue_name}'
        else:
            assert not received_task, \
                f'Task with state "{task.state}" is received from unexpected queue: {queue_name}'


def test_task_queues_range():
    # Task states validation range
    expected_sates = ('created', 'started', 'processed', 'done', 'postponed')
    assert len(TaskState.STATES) == len(expected_sates), 'Task states range less than expected one'
    for state in expected_sates:
        assert state in TaskState.STATES, f'State "{state}" is missing in actual state list'
    # Task queue presence in Task Processor
    task_processor = TaskProcessor()
    for task_type in (NetworkTask.__name__, SystemTask.__name__):
        assert task_type in task_processor.queues, f'Task type section {task_type} is missing in queue dict'
        for state in expected_sates:
            assert state in task_processor.queues[task_type], \
                f'Task queue for state "{state}" is missing in {task_type} section'


@pytest.mark.parametrize('task_name, task_type',
        [
            pytest.param(SYS_CMD_NAME, SystemTask.__name__, id=SystemTask.__name__),
            pytest.param(NET_CMD_NAME, NetworkTask.__name__, id=NetworkTask.__name__)
        ]
)
def test_task_queues(task_name: str, task_type: str):
    def validate_task_in_queue(state: str):
        assert task.state == state, 'Task state validation failure'
        task_from_queue = next(task_processor.queues[task_type][state])
        assert task_from_queue == task, 'Task does not corresponds to expected one'
        validate_task_queue(task, task_processor.queues[task_type][state], task_processor)
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[task_name]
    # Created task
    task = cmd.create_task()
    validate_task_in_queue(TaskState.CREATED)
    # Started task
    task.started = now()
    task.save()
    validate_task_in_queue(TaskState.STARTED)
    # Processed task
    task.processed = now()
    task.save()
    validate_task_in_queue(TaskState.PROCESSED)
    # Done task
    task.done = now()
    task.save()
    validate_task_in_queue(TaskState.DONE)


@pytest.mark.parametrize('task_name, task_type',
        [
            pytest.param(SYS_CMD_NAME, SystemTask.__name__, id=SystemTask.__name__),
            pytest.param(NET_CMD_NAME, NetworkTask.__name__, id=NetworkTask.__name__)
        ]
)
def test_postponed_task(task_name: str, task_type: str):
    def validate_task_in_queue(state: str):
        assert task.state == state, 'Task state validation failure'
        task_from_queue = next(task_processor.queues[task_type][state])
        assert task_from_queue == task, 'Task does not corresponds to expected one'
        validate_task_queue(task, task_processor.queues[task_type][state], task_processor)

    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[task_name]
    # Created task
    task = cmd.create_task()
    task.postponed = now()
    task.save()
    validate_task_in_queue(TaskState.POSTPONED)
    # Started task
    task.started = now()
    task.save()
    validate_task_in_queue(TaskState.POSTPONED)
    # Processed task
    task.processed = now()
    task.save()
    validate_task_in_queue(TaskState.POSTPONED)
    # Done task
    task.done = now()
    task.save()
    validate_task_in_queue(TaskState.POSTPONED)


def test_task_start():
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[SYS_CMD_NAME]
    init_task = cmd.create_task()
    task_processor.start_task(init_task)
    assert init_task.arguments == 'relay, relay', 'On start command flow is not applied'
    assert init_task == next(task_processor.queues[SystemTask.__name__][TaskState.STARTED]), \
        'Started task is missing in started tasks queue'
    children = init_task.get_children()
    assert len(children) == 2, 'Child tasks count mismatch'
    for child_task in children:
        assert isinstance(child_task, NetworkTask), 'Child task type mismatch'
        assert child_task.name == cmd.child_tasks[0], 'Child task name mismatch'
        assert next(task_processor.queues[NetworkTask.__name__][TaskState.CREATED]), \
            'Child task did not appear in "created" task queue'


def test_child_task_creation():
    pass


def test_task_finalization():
    pass


def test_task_lifecycle():
    pass
