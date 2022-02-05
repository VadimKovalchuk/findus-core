import json
import logging

from copy import deepcopy
from typing import Callable, List
from pathlib import Path

from task.lib.processing import get_function

logger = logging.getLogger('task_processor')

JSON_FOLDER = Path('data/task')
COMMANDS_JSON = {}
COMMANDS = {}


def collect_json(json_folder: Path) -> dict:
    result = {}
    for file in json_folder.rglob('*.json'):
        result.update(json.load(open(file)))
    return result


def get_cmd_dict(name: str) -> dict:
    result = COMMANDS_JSON.get(name)
    if result:
        return deepcopy(result)


def compose_command_dict(name: str) -> dict:
    # logger.debug(f'Collecting command "{name}" data')
    cmd_dict = get_cmd_dict(name)
    base_name = cmd_dict.get('base')
    if base_name:
        base_dict = compose_command_dict(base_name)
        for key, value in cmd_dict.items():
            base_dict[key] = deepcopy(value)
        return base_dict
    else:
        return cmd_dict


class Command:
    def __init__(self, name: str):
        cmd_dict = compose_command_dict(name)
        self.name: str = name
        self.dcn_task: bool = cmd_dict['dcn_task']
        self.run_on_start: List[Callable] = [get_function(func_name) for func_name in cmd_dict['run_on_start']]
        self.child_tasks: List[str] = cmd_dict['child_tasks']
        self.module: str = cmd_dict['module']
        self.function: str = cmd_dict['function']
        self.arguments: str = cmd_dict['arguments']
        logger.debug(cmd_dict['run_on_done'])
        self.run_on_done: List[Callable] = [get_function(func_name) for func_name in cmd_dict['run_on_done']]

    def __str__(self):
        return str(self.__dict__)


COMMANDS_JSON = collect_json(JSON_FOLDER)
COMMANDS = {cmd_name: Command(cmd_name) for cmd_name in COMMANDS_JSON}
