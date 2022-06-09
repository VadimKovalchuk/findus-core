import logging

from django.core.management.base import BaseCommand

from task.lib.task_processor import TaskProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        task_processor = TaskProcessor()
        while True:
            if not task_processor.wait_db_connection():
                continue
            task_processor.init_cycle()
            task_processor.processing_cycle()
            task_processor.finalize_cycle()
