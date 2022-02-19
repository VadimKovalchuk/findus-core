import logging

from datetime import datetime, timedelta
from typing import Callable, Generator, Union

from django.utils.timezone import now

from task.lib.commands import COMMANDS, Command
from task.lib.constants import TaskType, TASK_PROCESSING_QUOTAS
from task.lib.db import DatabaseMixin, compose_queryset_gen
from task.lib.processing import CommonServiceMixin
from task.models import SystemTask, NetworkTask, TaskState

logger = logging.getLogger(__name__)


class TaskProcessor(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queues = {
            TaskType.System: {state: compose_queryset_gen(state, SystemTask) for state in TaskState.STATES},
            TaskType.Network: {state: compose_queryset_gen(state, NetworkTask) for state in TaskState.STATES}
        }
        self._proc_candidates = set()
        self.quotas = TASK_PROCESSING_QUOTAS
        self.stages = (
            (self.start_task, TaskState.CREATED),
            (self.finalize_task, TaskState.PROCESSED),
            (self.set_processed, ''),
            (self.cancel_postpone, TaskState.POSTPONED),
            # (lambda x: x, TaskState.DONE),
        )

    def start_task(self, task: Union[SystemTask, NetworkTask]):
        logger.debug(f'Starting task: {task}')
        command = COMMANDS[task.name]
        for child_task_name in command.child_tasks:
            child_cmd: Command = COMMANDS[child_task_name]
            child_cmd.create_task(task)
            self.idle = False
        if command.on_start(task):
            logger.info(f'{task} is started')
            task.started = now()
            task.save()
            self.idle = False
        else:
            task.postponed = now() + timedelta(days=1)
            task.save()
            # TODO: Generate Event entry in DB
            logger.error(f'{task} start failure')
            raise SystemError('Task start failure')

    def set_processed(self):
        for task in self._proc_candidates:
            self.idle = False
            if task.is_processed():
                task.processed = now()
                task.save()
                self._proc_candidates.remove(task)

    def finalize_task(self, task: Union[SystemTask, NetworkTask]):
        logger.info(f'Finalizing task "{task.name}"({task.id})')
        command: Command = COMMANDS[task.name]
        if command.finalize(task):
            task.done = now()
            task.save()
            self.idle = False
            logger.info(f'{task} is completed')
            if task.parent_task:
                self._proc_candidates.add(task.parent_task)
        else:
            task.postponed = now() + timedelta(days=1)
            task.save()
            raise SystemError(f'Command {task.name} on_done flow failed')

    def cancel_postpone(self, task: Union[SystemTask, NetworkTask]):
        task.postponed = None
        task.save()

    def processing_cycle(self):
        for stage_handler, task_state in self.stages:
            for task_type in TaskType.ALL:
                self.generic_stage_handler(stage_handler, task_type, task_state)
