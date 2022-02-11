import logging
from time import sleep
from typing import Callable, Generator, List, Union

from django.db import connection, OperationalError
from django.db.models.query import QuerySet
from django.utils.timezone import now

from task.models import NetworkTask, SystemTask, TaskState

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


def generic_query_set_generator(
        query_getter: Callable,
        task_model: Union[SystemTask, NetworkTask]) -> Generator:
    while True:
        query_set = query_getter(task_model)
        if query_set:
            for task in query_set:
                yield task
        else:
            yield None


def get_created_tasks(task_model: Union[NetworkTask,SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(started__isnull=True)
    query_set = query_set.filter(postponed__isnull=True)
    query_set = query_set.order_by('created')
    return query_set


def created_sys_tasks() -> Generator:
    yield from generic_query_set_generator(get_created_tasks, SystemTask)


def get_started_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(started__isnull=False)
    query_set = query_set.filter(postponed__isnull=True)
    query_set = query_set.order_by('started')
    return query_set


def get_processed_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(done__isnull=True)
    query_set = query_set.filter(processed__isnull=False)
    query_set = query_set.filter(postponed__isnull=True)
    query_set = query_set.order_by('processed')
    return query_set


def get_postponed_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(postponed__lt=now())
    query_set = query_set.order_by('postponed')
    return query_set


def get_completed_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(done__isnull=False)
    query_set = query_set.filter(postponed__isnull=True)
    query_set = query_set.order_by('done')
    return query_set


QUERYSET_MAP = {
    TaskState.CREATED: get_created_tasks,
    TaskState.STARTED: get_started_tasks,
    TaskState.PROCESSED: get_processed_tasks,
    TaskState.DONE: get_completed_tasks,
    TaskState.POSTPONED: get_postponed_tasks
}


def compose_queryset_gen(task_state: str, task_model: Union[NetworkTask, SystemTask]):
    getter = QUERYSET_MAP[task_state]
    yield from generic_query_set_generator(getter, task_model)
