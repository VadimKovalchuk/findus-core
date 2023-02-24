import logging
from datetime import timedelta
from time import sleep
from typing import Callable, Generator, List, Union

from django.db import connection, OperationalError
from django.db.models.query import QuerySet
from django.utils.timezone import now

from task.models import NetworkTask, SystemTask, TaskState

logger = logging.getLogger('task_db_tools')


class DatabaseMixin:

    @property
    def db_connected(self):
        try:
            connection.ensure_connection()
            return True
        except OperationalError:
            logger.error(f'Database unavailable')
            return False

    def wait_db_connection(self, delay: int = 10, retry_count: int = 30):
        _try = 0
        while not self.db_connected:
            if _try == retry_count:
                logger.error('Permanent database connection failure')
                return False
            sleep(delay)
            _try += 1
        logger.info('Database connection reached')
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


def get_created_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.CREATED)
    query_set = query_set.order_by('id')
    return query_set


def get_started_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.STARTED)
    query_set = query_set.order_by('id')
    return query_set


def get_processed_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.PROCESSED)
    query_set = query_set.order_by('id')
    return query_set


def get_postponed_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(postponed__lt=now())
    query_set = query_set.order_by('postponed')
    return query_set


def get_completed_tasks(task_model: Union[NetworkTask, SystemTask]) -> QuerySet:
    query_set = task_model.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.DONE)
    query_set = query_set.order_by('id')
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


def get_pending_network_tasks(task_model: NetworkTask) -> QuerySet:
    query_set = task_model.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.STARTED)
    query_set = query_set.filter(sent__isnull=True)
    query_set = query_set.order_by('id')
    return query_set


def get_overdue_network_tasks(task_model: NetworkTask) -> QuerySet:
    query_set = task_model.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.STARTED)
    query_set = query_set.filter(sent__lt=now() - timedelta(days=1))
    query_set = query_set.order_by('id')
    return query_set


def pending_network_tasks():
    yield from generic_query_set_generator(get_pending_network_tasks, NetworkTask)


def overdue_network_tasks():
    yield from generic_query_set_generator(get_overdue_network_tasks, NetworkTask)
