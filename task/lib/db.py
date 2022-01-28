import logging
from time import sleep
from typing import Generator, List

from django.db import connection, OperationalError

from task.models import NetworkTask

logger = logging.getLogger('task_db_tools')


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
            logger.error(f'Database unavailable')
            return False

    def ensure_db_connection(self, delay: int = 10, retry_count: int = 30):
        _try = 0
        while not self.db_connected:
            if _try == retry_count:
                return False
            sleep(delay)
        logger.info('Database connection reached')
        for _ in range(5):
            if not self.db_connected:
                return False
            sleep(1)
        logger.info('Database connection is stable')
        return True


def get_ready_to_send_tasks() -> List[NetworkTask]:
    query_set = NetworkTask.objects.filter(started__isnull=True)
    query_set = query_set.filter(postponed__isnull=True)
    query_set = query_set.order_by('created')
    return query_set


def pending_tasks() -> Generator:
    while True:
        query_set = get_ready_to_send_tasks()
        if query_set:
            for task in query_set:
                yield task
        else:
            yield None
