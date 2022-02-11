import logging

from typing import Generator

from django.utils.timezone import now

from client.client import Client
from common.broker import Task
from task.lib.db import DatabaseMixin, compose_queryset_gen
from task.models import NetworkTask, TaskState

logger = logging.getLogger('dcn_client')


class NetworkClient(Client, DatabaseMixin):
    def __init__(self, name: str = 'findus-core', dsp_host: str = 'dispatcher', dsp_port: int = 9999,
                 token: str = 'docker'):
        super().__init__(name, token, dsp_host, dsp_port)
        self.idle = False
        self._active = True
        self.pending_tasks: Generator = compose_queryset_gen(TaskState.STARTED, NetworkTask)
        self.task_results: Generator = self._pull_task_result()

    @property
    def online(self):
        return self.db_connected and self.broker.connected

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
        logger.debug(str(dcn_task))
        self.broker.push(dcn_task)
        network_task.started = now()
        network_task.save()
        return True
