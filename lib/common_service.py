import logging
from time import sleep
from typing import Callable

from task.lib.constants import IDLE_SLEEP_TIMEOUT


logger = logging.getLogger('task_processor')


class CommonServiceMixin:
    def __init__(self):
        self.idle = False
        self._active = True

    def init_cycle(self):
        self.idle = True

    def finalize_cycle(self):
        if self.idle:
            logger.debug('Processing cycle is idle.')
            sleep(IDLE_SLEEP_TIMEOUT)

    def generic_stage_handler(self, func: Callable, state: str):
        task_limit = self.quotas[state]
        queue = self.queues[state]
        for _ in range(task_limit):
            task = next(queue)
            if task and self._active:
                self.idle = False
                return func(task)
            else:
                return True
