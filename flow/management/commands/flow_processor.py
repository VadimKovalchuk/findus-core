import logging

from time import sleep
from django.core.management.base import BaseCommand

from flow.lib.flow_processor import FlowProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        flow_processor = FlowProcessor()
        while True:
            if not flow_processor.db_connected and not flow_processor.wait_db_connection():
                continue
            flow_processor.init_cycle()
            flow_processor.processing_cycle()
            flow_processor.finalize_cycle()
