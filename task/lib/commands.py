import logging

from copy import deepcopy
from typing import Callable, List, Union
from pathlib import Path

from lib.file_processing import collect_json
from schedule.lib.interface import Scheduler
from task.models import Task, SystemTask, NetworkTask
from task.lib.processing import FUNCTIONS

logger = logging.getLogger('task_processor')

JSON_FOLDER = Path('data/task')
COMMANDS_JSON = {}
COMMANDS = {}


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
        logger.info(f'Creating Command: {name}')
        self.name: str = name
        self.dcn_task: bool = cmd_dict['dcn_task']
        self.run_on_start: List[Callable] = [FUNCTIONS[func_name] for func_name in cmd_dict['run_on_start']]
        self.child_tasks: List[str] = cmd_dict['child_tasks']
        self.module: str = cmd_dict['module']
        self.function: str = cmd_dict['function']
        self.arguments: dict = cmd_dict['arguments']
        self.run_on_done: List[Callable] = [FUNCTIONS[func_name] for func_name in cmd_dict['run_on_done']]

    def create_task(self, parent: Union[Task, None] = None):
        logger.info(f'Creating task: {self.name}')
        if self.dcn_task:
            task: NetworkTask = NetworkTask.objects.create(name=self.name)
            task.module = self.module
            task.function = self.function
        else:
            task = SystemTask.objects.create(name=self.name)
        if parent:
            task.parent_task = parent
        task.save()
        return task

    def on_start(self, task: Task) -> bool:
        for func in self.run_on_start:
            if not self._apply_callable(task, func):
                logger.error(f"Failure on start function: {func.__name__}")
                return False
        else:
            return True

    def finalize(self, task: Task) -> bool:
        for func in self.run_on_done:
            if not self._apply_callable(task, func):
                logger.error(f"Failure on finalisation function: {func.__name__}")
                return False
        else:
            return True

    def _apply_callable(self, task: Task, func: Callable) -> bool:
        try:
            return func(task)
        except Exception as exc:
            # TODO: Create corresponding Event enry in DB
            logger.error(exc.args)
            sched = Scheduler(f"Task {task} processing failure: {func.__name__}", str(exc.args))
            sched.push()
            return False

    def __str__(self):
        return str(self.__dict__)


COMMANDS_JSON = collect_json(JSON_FOLDER)
COMMANDS = {cmd_name: Command(cmd_name) for cmd_name in COMMANDS_JSON}
