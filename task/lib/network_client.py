import json
import logging

from typing import Callable, Dict

from django.utils.timezone import now

from dcn.client.client import Client
from task.lib.constants import TaskType, TASK_PROCESSING_QUOTAS
from lib.db import DatabaseMixin, overdue_network_tasks, pending_network_tasks
from lib.common_service import CommonServiceMixin
from task.models import NetworkTask, TaskState

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
            TaskState.STARTED: pending_network_tasks(),
            TaskState.PROCESSED: self._pull_task_result(),
            OVERDUE: overdue_network_tasks()  # TODO: not implemented
        }
        self.quotas = TASK_PROCESSING_QUOTAS
        self.stages = (
            (self.push_task_to_network, TaskState.STARTED),
            # (self.finalize_task, OVERDUE),
            (self.append_task_result_to_db, TaskState.PROCESSED),
        )

    @property
    def online(self):
        return self.db_connected and self.broker and self.broker.is_connected

    def _pull_task_result(self):
        while self._active:
            # for status, task in self.broker.pull():
            #     # TODO: Handle broker status
            #     yield task
            status, task = self.broker.consume()
            yield task

    def append_task_result_to_db(self, dcn_task: Dict):
        self.idle = False
        task_id = dcn_task['id']
        task: NetworkTask = NetworkTask.objects.get(pk=task_id)
        logger.info(f'Task {task.name} execution results received')
        task.result = dcn_task['result']
        task.state = TaskState.PROCESSED
        task.save()
        return True

    def push_task_to_network(self, network_task: NetworkTask):
        self.idle = False
        logger.info(f'Sending task: {network_task.name}')
        dcn_task = network_task.compose_for_dcn(self.name)
        dcn_task['client'] = self.broker.queue
        self.broker.publish(dcn_task)
        network_task.sent = now()
        network_task.save()
        return True

    def processing_cycle(self):
        for stage_handler, task_state in self.stages:
            self.generic_stage_handler(stage_handler, task_state)
