import logging
from time import sleep
from typing import Callable, Generator, List

from django.db import connection, OperationalError
from django.db.models.query import QuerySet

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


def generic_query_set_generator(query_getter: Callable) -> QuerySet:
    while True:
        query_set = query_getter()
        if query_set:
            for task in query_set:
                yield task
        else:
            yield None


def get_ready_to_send_tasks() -> QuerySet[NetworkTask]:
    query_set = NetworkTask.objects.filter(started__isnull=False)
    query_set = query_set.filter(postponed__isnull=True)
    query_set = query_set.order_by('created')
    return query_set


def pending_network_tasks() -> Generator:
    yield from generic_query_set_generator(get_ready_to_send_tasks)


def get_processed_network_tasks() -> List[NetworkTask]:
    query_set = NetworkTask.objects.filter(done__isnull=True)
    query_set = query_set.filter(processed__isnull=False)
    query_set = query_set.order_by('processed')
    return query_set


def processed_network_tasks() -> Generator:
    yield from generic_query_set_generator(get_processed_network_tasks)

