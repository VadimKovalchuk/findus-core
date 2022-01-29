import logging
from time import sleep

from django.core.management.base import BaseCommand


from task.lib.db import wait_for_db_active, get_processed_network_tasks
from task.processing import (
    finalize_task,
    get_new_system_tasks,
    start_task,
    get_postponed_tasks
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        wait_for_db_active()
        while True:
            # Validate completed tasks and process all (once a second)
            done_tasks = get_processed_network_tasks()
            # Once a minute do search for tasks with all completed children
            # done_tasks.extend(search_tasks_with_completed_child())
            # Collect list of tasks that has completed children
            # Validate parent tasks whether they has all child tasks completed and do post processing
            # tasks_may_be_done = {finalize_task(task) for task in done_tasks}
            # At this stage done from child task each time task is done
            for task in done_tasks:
                finalize_task(task)
            # Get not-started tasks and init preprocessing for all
            new_tasks = get_new_system_tasks()
            for task in new_tasks:
                logger.debug(f'Starting task "{task.name}" processing')
                start_task(task)
            # Validate postponed tasks and init processing for all
            postponed_tasks = get_postponed_tasks()
            for task in postponed_tasks:
                start_task(task)
            # If no events occurred - idle for 10 seconds
            if not any((done_tasks, new_tasks)):  # , postponed_tasks
                logger.debug('Idle.')
                sleep(10)
        # self.stdout.write(self.style.SUCCESS('done'))
