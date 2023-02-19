import logging

from django.core.management.base import BaseCommand

from schedule.lib.scheduler import SchedulerEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        scheduler = SchedulerEngine()
        while True:
            if not scheduler.db_connected and not scheduler.wait_db_connection():
                continue
            scheduler.init_cycle()
            scheduler.processing_cycle()
            scheduler.finalize_cycle()
