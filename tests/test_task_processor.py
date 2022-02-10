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


def validate_task_state(task: Task, expected_state: str):
    actual_state = task.state
    assert actual_state == expected_state, 'Task state validation failure'


def validate_task_queue(task: Task, expected_queue: Generator, task_proc: TaskProcessor):
    queues = [task_proc.created_sys_tasks, task_proc.started_sys_task]


def test_task_queues():
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[SYS_CMD_NAME]
    task = cmd.create_task()
    validate_task_state(task, TaskState.CREATED)
    task_from_queue = next(task_processor.created_tasks)
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
