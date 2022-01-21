import logging

from task.lib.db import DatabaseMixin

logger = logging.getLogger(__name__)


class TaskProcessor(DatabaseMixin):
    def __init__(self):
        self.db_connected = False

