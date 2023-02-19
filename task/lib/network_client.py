import logging

from typing import Callable

from django.utils.timezone import now

from dcn.client.client import Client
from dcn.common.broker import Task
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
            TaskType.Network: {
                TaskState.STARTED: pending_network_tasks(),
                TaskState.PROCESSED: self._pull_task_result(),
                OVERDUE: overdue_network_tasks()  # TODO: not implemented
            }
        }
        self.quotas = TASK_PROCESSING_QUOTAS
        self.stages = (
            (self.push_task_to_network, TaskState.STARTED),
            # (self.finalize_task, OVERDUE),
            (self.append_task_result_to_db, TaskState.PROCESSED),
        )

    @property
    def online(self):
        return self.db_connected and self.broker and self.broker.connected

    def _pull_task_result(self):
        while self._active:
            for result in self.broker.pulling_generator():
                yield result
            else:
                yield None

    def append_task_result_to_db(self, dcn_task: Task):
        self.idle = False
        task_id = dcn_task.body['id']
        task: NetworkTask = NetworkTask.objects.get(pk=task_id)
        logger.info(f'Task {task.name} execution results received')
        task.result = dcn_task.body['result']
        task.processed = now()
        task.save()
        self.broker.set_task_done(dcn_task)
        return True

    def push_task_to_network(self, network_task: NetworkTask):
        self.idle = False
        logger.info(f'Sending task: {network_task.name}')
        dcn_task = network_task.compose_for_dcn(self.name)
        dcn_task['client'] = self.broker.input_queue
        self.broker.push(dcn_task)
        network_task.sent = now()
        network_task.save()
        return True

    def stage_handler(self, func: Callable, task_state: str = ''):
        return self.generic_stage_handler(func, TaskType.Network, task_state)

    def processing_cycle(self):
        for stage_handler, task_state in self.stages:
            self.stage_handler(stage_handler, task_state)
