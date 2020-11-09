import logging
import sys

from django.core.management.base import BaseCommand, CommandError
from client.client import Client
from common.constants import CLIENT, BROKER, SECOND
from common.logging_tools import setup_module_logger
from task.models import Task

sys.path.append('./dcn')

modules = [__name__, 'client.py', BROKER]
for module_name in modules:
    setup_module_logger(module_name, logging.DEBUG)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        with Client(name='django', token='localhost') as client:
            client.connect()
            client.get_client_queues()
            for task in Task.objects.all():
                self.stdout.write(f'Got task: {task}')
                dcn_task = task.compose_for_dcn()
                dcn_task['client'] = client.broker.input_queue
                self.stdout.write(str(dcn_task))
                client.broker.push(dcn_task)
                result = next(client.broker.pulling_generator())
                client.broker.set_task_done(result)
                self.stdout.write(str(result))
        self.stdout.write(self.style.SUCCESS('done'))
