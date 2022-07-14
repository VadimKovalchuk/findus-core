import json
import logging

import pytest

from task.lib.commands import COMMANDS, COMMANDS_JSON, Command
from task.lib.processing import relay
from task.models import Task, NetworkTask, SystemTask

logger = logging.getLogger(__name__)

COMMANDS_COUNT = 9


def test_cmd_catalog():
    assert len(COMMANDS) == COMMANDS_COUNT, f"Unexpected commands count: {len(COMMANDS)}. Expected: {COMMANDS_COUNT}"
    logger.info("\n".join([cmd for cmd in COMMANDS]))


def test_cmd_diff_from_base():
    network_task_diff_lst = ['name', 'dcn_task', 'run_on_start', 'module', 'function', 'arguments', 'run_on_done']
    system_task_diff_lst = ['name', 'run_on_start', 'child_tasks', 'run_on_done']
    diff_map = (
        (COMMANDS['network_relay_task'], network_task_diff_lst),
        (COMMANDS['system_relay_task'], system_task_diff_lst),
    )
    parent_cmd = COMMANDS['base']
    for child_cmd, diff_lst in diff_map:
        for param, parent_value in parent_cmd.__dict__.items():
            child_value = getattr(child_cmd, param)
            if param in diff_lst:
                assert parent_value != child_value, \
                    f'Child value ({child_value}) for param {param} match one from parent ({parent_value})' \
                    f' when difference is expected'
            else:
                assert parent_value == child_value, \
                    f'Child value ({child_value}) for param {param} diff from one in parent ({parent_value})' \
                    f' when difference is expected'


@pytest.mark.django_db
@pytest.mark.parametrize('task_name, task_type',
        [
            pytest.param('network_relay_task', NetworkTask, id='network_task'),
            pytest.param('system_relay_task', SystemTask, id='system_task')
        ]
)
def test_create_task(
        task_name: str,
        task_type: Task
):
    command: Command = COMMANDS[task_name]
    task = command.create_task()
    task.arguments = 'test'
    task.save()
    assert task, 'Command instance has failed to create corresponding task'
    task_from_db = task_type.objects.get(name=command.name)
    assert task_from_db, 'Command issued task is missing in DB'
    assert task == task_from_db, 'Command issued task does not corresponds to one from DB'
    validation_list = ['name', 'module', 'function', 'argument'] if command.dcn_task else ['name', 'argument']
    for param in validation_list:
        cmd_value = command.__dict__.get(param)
        task_value = task.__dict__.get(param)
        logger.info(f'Parameter "{param}": command- {cmd_value}, task- {task_value}')
        assert cmd_value == task_value, \
            f'Parameter "{param}" differs. Command: {cmd_value}, Task: {task_value}'
    assert task.created, 'Task creation time is not defined'
    assert not task.started, 'Task is started when not expected'


@pytest.mark.django_db
@pytest.mark.parametrize('on_start, on_done, expected',
        [
            pytest.param([], [], None, id='empty'),
            pytest.param([relay], [], 'relay', id='single-on_start'),
            pytest.param([], [relay], 'relay', id='single-on_done'),
            pytest.param([relay], [relay], 'relay, relay', id='single-both'),
            pytest.param([relay, relay], [], 'relay, relay', id='multiple-on_start'),
            pytest.param([], [relay, relay], 'relay, relay', id='multiple-on_done'),
            pytest.param([relay, relay], [relay, relay], 'relay, relay, relay, relay', id='multiple-both'),
        ]
)
def test_wrapping_functions(
        on_start: list,
        on_done: list,
        expected: str
):
    command: Command = COMMANDS['system_relay_task']
    command.run_on_start = on_start
    command.run_on_done = on_done
    system_task: SystemTask = command.create_task()
    command.on_start(system_task)
    command.finalize(system_task)
    logger.info(
        f'arguments: {system_task.arguments}\n'
        f'result: {system_task.result}\n'
        f'expected: {expected}'
    )
    assert system_task.arguments == expected, 'Task arguments does not match expected ones'
    assert system_task.result == expected, 'Task result does not match expected ones'
