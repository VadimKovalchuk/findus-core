import logging

from datetime import datetime, timedelta
from typing import Generator, Union

from django.utils.timezone import now

from task.lib.commands import COMMANDS, Command
from task.lib.db import created_tasks, DatabaseMixin, postponed_tasks, processed_tasks, processed_network_tasks
from task.lib.processing import get_function
from task.models import SystemTask, NetworkTask

logger = logging.getLogger(__name__)


class TaskProcessor(DatabaseMixin):
    def __init__(self):
        self.idle = False
        self._active = True
        self.processed_network_tasks: Generator = processed_network_tasks()
        self.created_tasks: Generator = created_tasks()
        self.postponed_tasks: Generator = postponed_tasks()
        self.processed_candidates = set()
        self.processed_tasks: Generator = processed_tasks()

    def finalization_stage(self):
        pass

    def start_task(self, task: Union[SystemTask, NetworkTask]):
        logger.debug(f'Starting task: {task}')
        command = COMMANDS[task.name]
        for child_task_name in command.child_tasks:
            child_cmd: Command = COMMANDS[child_task_name]
            child_cmd.create_task(task)
        if command.on_start(task):
            logger.info(f'{task} is started')
            task.started = now()
            task.save()
        else:
            task.postponed = now() + timedelta(days=1)
            task.save()
            # TODO: Generate Event entry in DB
            logger.error(f'{task} start failure')
            raise SystemError('Task start failure')

    def finalize_task(self, task: Union[SystemTask, NetworkTask]):
        logger.info(f'Finalizing task "{task.name}"({task.id})')
        command: Command = COMMANDS[task.name]
        if not command.finalize(task):
            task.postponed = now() + timedelta(days=1)
            task.save()
            raise SystemError(f'Command {task.name} on_done flow failed')
        task.done = now()
        task.save()
        logger.info(f'{task} is completed')
        if task.parent_task:
            self.processed_candidates.add(task.parent_task)
