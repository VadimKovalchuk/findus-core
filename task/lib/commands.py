import json
import logging

from copy import deepcopy
from typing import List
from pathlib import Path

logger = logging.getLogger('task_processor')

JSON_FOLDER = Path('data/task')


def collect_json(json_folder: Path) -> dict:
    result = {}
    for file in json_folder.rglob('*.json'):
        key = file.name.replace('.json', '')
        result.update(json.load(open(file)))
    return result


COMMANDS_CATALOG = collect_json(JSON_FOLDER)


def get_cmd_dict(name: str) -> dict:
    result = COMMANDS_CATALOG.get(name)
    if result:
        return deepcopy(result)


def compose_command_dict(name: str) -> dict:
    logger.debug(f'Collecting command "{name}" data')
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
        self.name: str = name
        self.dcn_task: bool = None
        self.run_on_start: List[str] = None
        self.child_tasks: List[str] = None
        self.run_on_done: List[str] = None



