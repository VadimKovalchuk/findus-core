import logging

from typing import Generator, Union

from django.utils.timezone import now

from task.commands import commands
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

    def finalize_task(self, task: Union[SystemTask, NetworkTask]):
        logger.info(f'Finalizing task "{task.name}"({task.id})')
        command = commands[task.name]
        on_done = get_function(command['run_on_done'])(task) if command['run_on_done'] else True
        if not on_done:
            task.done = now()
            task.save()
            raise SystemError(f'Command {task.name} on_done flow failed')
        if isinstance(task, SystemTask) and not task.is_done():
            return
        if not task.done:
            task.done = now()
        task.processed = now()
        task.save()
        logger.info(f'{task} processing completed')
        if task.parent_task:
            self.processed_candidates.add(task.parent_task)

