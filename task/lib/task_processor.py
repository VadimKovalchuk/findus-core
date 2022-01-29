import logging

from typing import Generator

from django.utils.timezone import now

from task.lib.db import DatabaseMixin, processed_network_tasks
from task.models import SystemTask, NetworkTask

logger = logging.getLogger(__name__)


class TaskProcessor(DatabaseMixin):
    def __init__(self):
        self.idle = False
        self._active = True
        self.ready_network_tasks: Generator = processed_network_tasks()
        self.created_tasks: Generator = None
        self.postponed_tasks: Generator = None
        self.started_tasks: Generator = None
        self.processed_tasks: Generator = None

