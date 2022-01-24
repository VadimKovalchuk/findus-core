import logging

from django.utils.timezone import now

from client.client import Client
from common.broker import Task
from task.lib.db import DatabaseMixin, get_ready_to_send_tasks
from task.models import NetworkTask

logger = logging.getLogger('dcn_client')


class NetworkClient(DatabaseMixin):
    def __init__(self,
                 name: str = 'findus-core',
                 dsp_host: str = 'dispatcher',
                 dsp_port: int = 9999,
                 token: str = 'docker'):
        self.idle = False
        self.dcn = Client(name, token, dsp_host, dsp_port)
        self._active = True
        self._pending_tasks = []

    def __enter__(self):
        self.dcn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dcn.__exit__()

    @property
    def online(self):
        return self.db_connected and self.dcn.broker.connected

    def pull_task_result(self):
        for result in self.dcn.broker.pulling_generator():
            if self._active:
                yield result
            else:
                break

    def pull_pending_task(self):
        for task in self._pending_tasks:
            if self._active:
                yield task
            else:
                break
        else:
            self._pending_tasks = get_ready_to_send_tasks()

    def append_task_result_to_db(self, dcn_task: Task):
        task_id = dcn_task.body['id']
        task: NetworkTask = NetworkTask.objects.get(pk=task_id)
        logger.info(f'Task {task.name} execution results received')
        task.result = dcn_task.body['result']
        task.done = now()
        task.save()
        self.dcn.broker.set_task_done(dcn_task)

    def push_task_to_network(self, network_task: NetworkTask):
        logger.info(f'Sending task: {network_task.name}')
        dcn_task = network_task.compose_for_dcn()
        dcn_task['client'] = self.dcn.broker.input_queue
        logger.debug(str(dcn_task))
        self.dcn.broker.push(dcn_task)
        network_task.started = now()
        network_task.save()
