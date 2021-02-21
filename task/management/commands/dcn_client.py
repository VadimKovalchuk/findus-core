import logging
import sys

from django.utils.timezone import now
from time import sleep
from typing import List

from django.core.management.base import BaseCommand, CommandError
from client.client import Client
from common.constants import CLIENT, BROKER, SECOND
from common.logging_tools import setup_module_logger
from task.models import NetworkTask

sys.path.append('./dcn')

modules = [__name__, 'client.py', BROKER]
for module_name in modules:
    setup_module_logger(module_name, logging.DEBUG)
logger = logging.getLogger(__name__)


def get_ready_to_send_tasks() -> List[NetworkTask]:
    query_set = NetworkTask.objects.filter(started__isnull=True)
    query_set = query_set.order_by('created')
    tasks = [query_set.first()]
    return [task for task in tasks if task]


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        with Client(name='django', token='localhost') as client:
            client.connect()
            client.get_client_queues()
            client.broker._inactivity_timeout = 0.01
            while True:
                # Validate input queue and process completed tasks
                for result in client.broker.pulling_generator():
                    task_id = result.body['id']
                    task: NetworkTask = NetworkTask.objects.get(pk=task_id)
                    task.result = result.body['result']
                    task.done = now()
                    task.save()
                    client.broker.set_task_done(result)

                tasks = get_ready_to_send_tasks()
                for task in tasks:
                    self.stdout.write(f'Got task: {task.name}')
                    dcn_task = task.compose_for_dcn()
                    dcn_task['client'] = client.broker.input_queue
                    self.stdout.write(str(dcn_task))
                    client.broker.push(dcn_task)
                    task.started = now()
                    task.save()
                # self.stdout.write('Cycle done.')
                # sleep(1)
        self.stdout.write(self.style.SUCCESS('done'))
