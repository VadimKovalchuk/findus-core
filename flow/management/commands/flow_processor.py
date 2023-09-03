import logging

from django.core.management.base import BaseCommand

from flow.lib.flow_processor import FlowProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        task_processor = FlowProcessor()
        while True:
            if not task_processor.db_connected and not task_processor.wait_db_connection():
                continue
            task_processor.init_cycle()
            task_processor.processing_cycle()
            task_processor.finalize_cycle()
