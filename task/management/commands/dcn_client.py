import logging

from django.utils.timezone import now
from time import sleep

from django.core.management.base import BaseCommand

from client.client import Client
from common.constants import CLIENT, BROKER
from common.logging_tools import setup_module_logger
from task.models import NetworkTask
from task.lib.db import wait_for_db_active, get_ready_to_send_tasks

modules = [(__name__, logging.DEBUG),
           (CLIENT, logging.DEBUG),
           (BROKER, logging.INFO)]
for module_name, level in modules:
    setup_module_logger(module_name, level)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        wait_for_db_active()
        with Client(name='django', dsp_ip='dispatcher', token='docker') as client:
            # client.connect()
            while not client.broker:
                client.get_client_queues()
                sleep(10)
            client.broker._inactivity_timeout = 0.01
            while True:
                idle = True
                # Validate input queue and process completed tasks
                for result in client.broker.pulling_generator():
                    task_id = result.body['id']
                    task: NetworkTask = NetworkTask.objects.get(pk=task_id)
                    logger.info(f'Task {task.name} execution results received')
                    task.result = result.body['result']
                    task.done = now()
                    task.save()
                    client.broker.set_task_done(result)
                    idle = False
                # Shoot ready to send tasks
                tasks = get_ready_to_send_tasks()
                for task in tasks:
                    self.stdout.write(f'Sending task: {task.name}')
                    dcn_task = task.compose_for_dcn()
                    dcn_task['client'] = client.broker.input_queue
                    self.stdout.write(str(dcn_task))
                    client.broker.push(dcn_task)
                    task.started = now()
                    task.save()
                    idle = False
                logger.debug('Cycle done.')
                # If no events occurred - idle for 10 seconds
                if idle:
                    sleep(10)  # seconds
        # self.stdout.write(self.style.SUCCESS('done'))
