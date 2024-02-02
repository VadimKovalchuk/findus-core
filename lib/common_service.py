import logging
from time import sleep
from typing import Callable

IDLE_TIMEOUT_PROGRESSIVE = [0, 1, 3, 10]

logger = logging.getLogger('processing')


class CommonServiceMixin:
    def __init__(self):
        self.idle = False
        self._active = True
        self.idle_period = 0

    def init_cycle(self):
        self.idle = True

    def _calculate_idle_period(self):
        previous_index = IDLE_TIMEOUT_PROGRESSIVE.index(self.idle_period)
        if previous_index < len(IDLE_TIMEOUT_PROGRESSIVE) - 1:
            self.idle_period = IDLE_TIMEOUT_PROGRESSIVE[previous_index + 1]

    def finalize_cycle(self):
        if self.idle:
            self._calculate_idle_period()
            if self.idle_period == IDLE_TIMEOUT_PROGRESSIVE[-1]:
                logger.debug(f'Processing cycle is idle for {self.idle_period} sec')
            sleep(self.idle_period)
        else:
            self.idle_period = 0

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
