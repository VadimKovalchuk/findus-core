import logging

from typing import Generator

from django.utils.timezone import now

from task.lib.db import created_tasks, DatabaseMixin, postponed_tasks, processed_tasks, processed_network_tasks
from task.models import SystemTask, NetworkTask

logger = logging.getLogger(__name__)


class TaskProcessor(DatabaseMixin):
    def __init__(self):
        self.idle = False
        self._active = True
        self.processed_network_tasks: Generator = processed_network_tasks()
        self.created_tasks: Generator = created_tasks()
        self.postponed_tasks: Generator = postponed_tasks()
        self.processed_candidates = set()
        self.processed_tasks: Generator = processed_tasks()

