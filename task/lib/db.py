import logging
from time import sleep
from typing import List

from django.db import connection, OperationalError

from task.models import NetworkTask

logger = logging.getLogger('task_processor')


def wait_for_db_active():
    logger.info('Waiting for database')
    db_conn = None
    while not db_conn:
        try:
            connection.ensure_connection()
            db_conn = True
        except OperationalError:
            logger.info('Database unavailable, waiting 1 second...')
            sleep(1)
    logger.info('Database connection reached')


class DatabaseMixin:

    @property
    def db_connected(self):
        try:
            connection.ensure_connection()
            return True
        except OperationalError:
            logger.info(f'Database unavailable')
            return False


def get_ready_to_send_tasks() -> List[NetworkTask]:
    query_set = NetworkTask.objects.filter(started__isnull=True)
    query_set = query_set.order_by('created')
    tasks = [query_set.first()]
    return [task for task in tasks if task]
