import logging
from time import sleep

from django.core.management.base import BaseCommand

from schedule.lib.scheduler import ScheduleProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        scheduler = ScheduleProcessor()
        while True:
            if not scheduler.db_connected and not scheduler.wait_db_connection():
                sleep(1)
                continue
            scheduler.init_cycle()
            scheduler.processing_cycle()
            scheduler.finalize_cycle()
