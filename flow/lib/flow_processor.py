import logging

from datetime import timedelta
from typing import Union

from django.utils.timezone import now

from task.lib.commands import COMMANDS, Command
from task.lib.constants import TaskType, TASK_PROCESSING_QUOTAS
from lib.db import DatabaseMixin, compose_queryset_gen
from lib.common_service import CommonServiceMixin
from task.models import SystemTask, NetworkTask, TaskState

logger = logging.getLogger(__name__)


class FlowProcessor(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queues = {
            TaskType.System: {state: compose_queryset_gen(state, SystemTask) for state in TaskState.states},
            TaskType.Network: {state: compose_queryset_gen(state, NetworkTask) for state in TaskState.states}
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
        logger.info(f'Starting task: {task}')
        command = COMMANDS[task.name]
        for child_task_name in command.child_tasks:
            child_cmd: Command = COMMANDS[child_task_name]
            child_cmd.create_task(task)
            self.idle = False
        if command.on_start(task):
            logger.debug(f'{task} is started')
            task.state = TaskState.STARTED
            task.save()
            self.idle = False
        else:
            task.postponed = now() + timedelta(days=1)
            task.save()
            logger.error(f'{task} start failure')
            # raise SystemError('Task start failure')

    def set_processed(self):
        for task in self._proc_candidates:
            self.idle = False
            if task.is_processed():
                task.refresh_from_db()
                task.state = TaskState.PROCESSED
                task.save()
        self._proc_candidates = set()

    def finalize_task(self, task: Union[SystemTask, NetworkTask]):
        logger.info(f'Finalizing task "{task.name}"({task.id})')
        command: Command = COMMANDS[task.name]
        if command.finalize(task):
            task.state = TaskState.DONE
            task.save()
            self.idle = False
            logger.info(f'{task} is completed')
            if task.parent_task:
                self._proc_candidates.add(task.parent_task)
        else:
            task.postponed = now() + timedelta(days=1)
            task.save()
            logger.error(f'Command {task.name} on_done flow failed')
            #raise SystemError(f'Command {task.name} on_done flow failed')

    def cancel_postpone(self, task: Union[SystemTask, NetworkTask]):
        task.postponed = None
        task.save()

    def processing_cycle(self):
        for stage_handler, task_state in self.stages:
            for task_type in TaskType.ALL:
                self.generic_stage_handler(stage_handler, task_type, task_state)
