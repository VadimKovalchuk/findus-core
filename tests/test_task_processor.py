import logging

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


def validate_task_state(task: Task, expected_state: str):
    actual_state = task.state
    assert actual_state == expected_state, 'Task state validation failure'


def validate_task_queue(task: Task, expected_queue: Generator, task_proc: TaskProcessor):
    queues = [task_proc.created_sys_tasks, task_proc.started_sys_task]


def test_task_queues_range():
    # Task states validation range
    expected_sates = ('created', 'started', 'processed', 'done', 'postponed')
    assert len(TaskState.STATES) >= len(expected_sates), 'Task states range less than expected one'
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
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[task_name]
    task = cmd.create_task()
    validate_task_state(task, TaskState.CREATED)
    task_from_queue = next(task_processor.queues[task_type][TaskState.CREATED])
    assert task_from_queue == task, 'Task does not corresponds to expected one'
    task.started = now()
    task.save()

    validate_task_state(task, TaskState.STARTED)
    task.processed = now()
    task.save()
    validate_task_state(task, TaskState.PROCESSED)
    task.done = now()
    task.save()
    validate_task_state(task, TaskState.DONE)


def test_postponed_task():
    pass


def test_task_start():
    pass


def test_child_task_creation():
    pass


def test_task_finalization():
    pass


def test_task_lifecycle():
    pass
