import logging
from datetime import timedelta
from time import sleep
from typing import Callable, Generator

from django.db import connection, OperationalError
from django.db.models.query import QuerySet
from django.utils.timezone import now

from flow.models import Flow, FlowState
from task.models import NetworkTask, TaskState

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


def generic_query_set_generator(query_getter: Callable) -> Generator:
    while True:
        query_set = query_getter()
        if query_set:
            for task in query_set:
                yield task
        else:
            yield None


def get_pending_network_tasks() -> QuerySet:
    query_set = NetworkTask.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.CREATED)
    query_set = query_set.filter(sent__isnull=True)
    query_set = query_set.order_by('id')
    return query_set


def get_overdue_network_tasks() -> QuerySet:
    query_set = NetworkTask.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=TaskState.STARTED)
    query_set = query_set.filter(sent__lt=now() - timedelta(days=1))
    query_set = query_set.order_by('id')
    return query_set


def pending_network_tasks():
    yield from generic_query_set_generator(get_pending_network_tasks)


def overdue_network_tasks():
    yield from generic_query_set_generator(get_overdue_network_tasks)


def get_created_flows() -> QuerySet:
    query_set = Flow.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=FlowState.CREATED)
    query_set = query_set.order_by('id')
    return query_set


def get_running_flows() -> QuerySet:
    query_set = Flow.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=FlowState.RUNNING)
    query_set = query_set.order_by('id')
    return query_set


def get_postponed_flows() -> QuerySet:
    query_set = Flow.objects.filter(postponed__lt=now())
    query_set = query_set.order_by('postponed')
    return query_set


def get_done_flows() -> QuerySet:
    query_set = Flow.objects.filter(postponed__isnull=True)
    query_set = query_set.filter(processing_state=FlowState.DONE)
    query_set = query_set.order_by('id')
    return query_set
