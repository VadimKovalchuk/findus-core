import json
import logging

from datetime import timedelta
from typing import Dict

from django.utils.timezone import now

from dcn.client.client import Client
from task.lib.constants import TASK_PROCESSING_QUOTAS
from lib.db import DatabaseMixin, overdue_tasks, pending_tasks, postponed_tasks, running_tasks
from lib.common_service import CommonServiceMixin
from task.models import Task, TaskState

logger = logging.getLogger('dcn_client')

OVERDUE = 'overdue'


class NetworkClient(Client, CommonServiceMixin, DatabaseMixin):
    def __init__(
            self,
            name: str = 'findus-core',
            dsp_host: str = 'dispatcher',
            dsp_port: int = 9999,
            token: str = 'docker'
    ):
        super().__init__(name, token, dsp_host, dsp_port)
        CommonServiceMixin.__init__(self)
        self.queues = {
            TaskState.CREATED: pending_tasks(),
            TaskState.STARTED: running_tasks(),
            TaskState.PROCESSED: self._pull_task_result(),
            OVERDUE: overdue_tasks(),  # TODO: not implemented
            TaskState.POSTPONED: postponed_tasks(),
        }
        self.quotas = TASK_PROCESSING_QUOTAS
        self.stages = (
            (self.push_task_to_network, TaskState.CREATED),
            (self.process_overdue, OVERDUE),
            (self.process_task_results, TaskState.PROCESSED),
            (self.process_postponed, TaskState.POSTPONED),
        )

    @property
    def online(self):
        return self.db_connected and self.broker and self.broker.is_connected

    def _pull_task_result(self):
        while self._active:
            status, task = self.broker.consume()
            yield task

    def process_task_results(self, dcn_task: Dict):

        def validate_failure(dcn_task: Dict):
            if dcn_task['status'] is False:
                logger.error(f'Task "{dcn_task["id"]}" has failed with error: {dcn_task.get("resolution")}')
                return False
            else:
                return True

        def append_result_to_db():
            task.result = dcn_task['result']
            task.state = TaskState.PROCESSED
            task.save()
            return True

        task_id = dcn_task['id']
        task: Task = Task.objects.get(pk=task_id)
        logger.info(f'Task {task.name} execution results received')
        if validate_failure(dcn_task):
            return append_result_to_db()
        else:
            task.postponed = now() + timedelta(hours=1)
            task.reset()
            return True


    def push_task_to_network(self, task: Task):
        logger.info(f'Sending task: {task.name}')
        dcn_task = task.compose_for_dcn(self.name)
        dcn_task['client'] = self.broker.queue
        self.broker.publish(dcn_task)
        task.sent = now()
        task.state = TaskState.STARTED
        task.save()
        return True

    def process_postponed(self, task: Task):
        logger.info(f'Task "{task.name}" postpone period expired')
        task.postponed = None
        task.save()
        return True

    def process_overdue(self, task: Task):
        task.reset()
        return True

    def processing_cycle(self):
        for stage_handler, task_state in self.stages:
            self.generic_stage_handler(stage_handler, task_state)
