import logging

from django.utils.timezone import now
from time import sleep

from django.core.management.base import BaseCommand
from task.lib.network_client import NetworkClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        client = NetworkClient(name='django', dsp_host='dispatcher', token='docker')
        while True:
            if not client.online:
                if not client.db_connected and not client.wait_db_connection():
                    continue
                if not (client.broker and client.broker.connected):
                    client.socket.establish()
                    for _ in range(5):
                        if client.get_client_queues():
                            break
                        sleep(10)
                    else:
                        continue
                    client.broker.connect()
                    client.broker.declare()
            client.init_cycle()
            client.processing_cycle()
            client.finalize_cycle()
        # self.stdout.write(self.style.SUCCESS('done'))
