import logging

from time import monotonic
from typing import Generator

import pytest

from django.utils.timezone import now

from task.lib.commands import COMMANDS, Command
from task.lib.constants import TaskType
from task.lib.network_client import NetworkClient
from task.lib.task_processor import TaskProcessor
from task.models import Task, SystemTask, NetworkTask, TaskState

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db

SYS_CMD_NAME = 'system_relay_task'
NET_CMD_NAME = 'network_relay_task'


def validate_task_queue(task: Task, expected_queue: Generator, task_proc: TaskProcessor):
    queues = {'net_' + queue_name: queue for queue_name, queue in task_proc.queues[TaskType.Network].items()}
    queues.update({'sys_' + queue_name: queue for queue_name, queue in task_proc.queues[TaskType.System].items()})
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
    assert len(TaskState.states) == len(expected_sates), 'Task states range less than expected one'
    for state in expected_sates:
        assert state in TaskState.states, f'State "{state}" is missing in actual state list'
    # Task queue presence in Task Processor
    task_processor = TaskProcessor()
    for task_type in TaskType.ALL:
        assert task_type in task_processor.queues, f'Task type section {task_type} is missing in queue dict'
        for state in expected_sates:
            assert state in task_processor.queues[task_type], \
                f'Task queue for state "{state}" is missing in {task_type} section'


@pytest.mark.parametrize('task_name, task_type',
        [
            pytest.param(SYS_CMD_NAME, TaskType.System, id=TaskType.System),
            pytest.param(NET_CMD_NAME, TaskType.Network, id=TaskType.Network)
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
    task.state = TaskState.STARTED
    task.save()
    validate_task_in_queue(TaskState.STARTED)
    # Processed task
    task.state = TaskState.PROCESSED
    task.save()
    validate_task_in_queue(TaskState.PROCESSED)
    # Done task
    task.state = TaskState.DONE
    task.save()
    validate_task_in_queue(TaskState.DONE)


@pytest.mark.parametrize('task_name, task_type',
        [
            pytest.param(SYS_CMD_NAME, TaskType.System, id=TaskType.System),
            pytest.param(NET_CMD_NAME, TaskType.Network, id=TaskType.Network)
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
    task.state = TaskState.STARTED
    task.save()
    validate_task_in_queue(TaskState.POSTPONED)
    # Processed task
    task.state = TaskState.PROCESSED
    task.save()
    validate_task_in_queue(TaskState.POSTPONED)
    # Done task
    task.state = TaskState.DONE
    task.save()
    validate_task_in_queue(TaskState.POSTPONED)


@pytest.mark.parametrize('task_name, task_type',
        [
            pytest.param(SYS_CMD_NAME, TaskType.System, id=TaskType.System),
            pytest.param(NET_CMD_NAME, TaskType.Network, id=TaskType.Network)
        ]
)
def test_task_start(task_name: str, task_type: str):
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[task_name]
    task = cmd.create_task()
    task_processor.generic_stage_handler(task_processor.start_task, task_type, TaskState.CREATED)
    task.refresh_from_db()
    assert task.arguments == "{\"arg\": \"test, relay, relay\"}", 'On start command flow is not applied'
    assert task == next(task_processor.queues[task_type][TaskState.STARTED]), \
        'Started task is missing in started tasks queue'
    assert not next(task_processor.queues[task_type][TaskState.CREATED]), \
        'Unexpected task is received from created tasks queue'


def test_child_task_creation():
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[SYS_CMD_NAME]
    task = cmd.create_task()
    task_processor.generic_stage_handler(task_processor.start_task, TaskType.System, TaskState.CREATED)
    task.refresh_from_db()
    children = task.get_children()
    assert len(children) == 2, 'Child tasks count mismatch'
    for child_task in children:
        assert isinstance(child_task, NetworkTask), 'Child task type mismatch'
        assert child_task.name == cmd.child_tasks[0], 'Child task name mismatch'
        assert next(task_processor.queues[TaskType.Network][TaskState.CREATED]), \
            'Child task did not appear in "created" task queue'


@pytest.mark.parametrize('task_name, task_type',
        [
            pytest.param(SYS_CMD_NAME, TaskType.System, id=TaskType.System),
            pytest.param(NET_CMD_NAME, TaskType.Network, id=TaskType.Network)
        ]
)
def test_task_finalization(task_name: str, task_type: str):
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[task_name]
    task = cmd.create_task()
    task.state = TaskState.PROCESSED
    task.save()
    task_processor.generic_stage_handler(task_processor.finalize_task, task_type, TaskState.PROCESSED)
    task.refresh_from_db()
    assert task.arguments == "{\"arg\": \"test, relay, relay\"}", 'On done command flow is not applied'
    assert task == next(task_processor.queues[task_type][TaskState.DONE]), \
        'Started task is missing in started tasks queue'
    assert not next(task_processor.queues[task_type][TaskState.PROCESSED]), \
        'Unexpected task is received from created tasks queue'


def test_processed_transition():
    task_processor = TaskProcessor()
    cmd: Command = COMMANDS[SYS_CMD_NAME]
    task: SystemTask = cmd.create_task()
    task_processor.start_task(task)
    for child in task.get_children():
        child.state = TaskState.DONE
        child.save()
    task.refresh_from_db()
    assert task.is_processed(), 'Task processed state is not reached on done children'
    task_processor._proc_candidates.add(task)
    task_processor.set_processed()
    assert task.state == TaskState.PROCESSED, 'Processed task has not reached "processed" state'
    assert not task_processor._proc_candidates, 'Processing candidates set in not cleared after processing'


def test_task_lifecycle(network_client_on_dispatcher: NetworkClient):
    task_proc = TaskProcessor()
    cmd: Command = COMMANDS[SYS_CMD_NAME]
    task: SystemTask = cmd.create_task()
    start = monotonic()
    while not task.state == TaskState.DONE and monotonic() < start + 5:
        task_proc.processing_cycle()
        network_client_on_dispatcher.processing_cycle()
        task.refresh_from_db()
    logger.info(monotonic() - start)
    children = task.get_children()
    assert children, 'Children tasks are not created'
    for child in children:
        assert child.state == TaskState.DONE, 'Child Network task is not in done state'
    assert task.state == TaskState.DONE, 'System task is not in done state'
