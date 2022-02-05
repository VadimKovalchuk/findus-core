import logging

import pytest

from task.lib.commands import COMMANDS, COMMANDS_JSON

logger = logging.getLogger(__name__)

COMMANDS_COUNT = 7


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
