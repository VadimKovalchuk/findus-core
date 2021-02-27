import logging
from time import sleep
from typing import List, Union

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from task.commands import commands
from task.models import NetworkTask, SystemTask
from task.processing import get_function

logger = logging.getLogger(__name__)


def create_task(name: str, parent_task: SystemTask = None):
    command = commands[name]
    if command['dcn_task']:
        task: NetworkTask = NetworkTask.objects.create(name=name)
        task.module = command['module']
        task.function = command['function']
    else:
        task = SystemTask.objects.create(name=name)
    if parent_task:
        task.priority = parent_task.priority
        task.arguments = parent_task.arguments
        task.parent_task = parent_task
        print([parent_task.systemtask_set.all(), parent_task.networktask_set.all()])
    on_start = get_function(command['run_on_start'])(task) if command['run_on_start'] else True
    if not on_start:
        raise CommandError(f'Command {name} on_start flow failed')
    task.save()
    print(f'Created: {task}')


def get_done_network_tasks() -> List[NetworkTask]:
    query_set = NetworkTask.objects.filter(done__isnull=False)
    query_set = query_set.filter(processed__isnull=True)
    return query_set


def search_tasks_with_completed_child(tasks: List[SystemTask]) -> List[SystemTask]:
    pass


def finalize_task(task: Union[SystemTask, NetworkTask]):
    command = commands[task.name]
    on_done = get_function(command['run_on_done'])(task)
    if not on_done:
        raise CommandError(f'Command {task.name} on_done flow failed')
    if isinstance(task, SystemTask) and not task.is_done():
        return
    if not task.done:
        task.done = now()
    task.processed = now()


def get_new_tasks() -> List[SystemTask]:
    query_set = SystemTask.objects.filter(started__isnull=True)
    return query_set


def start_task(task: List[SystemTask]):
    child_tasks = commands[task.name]['child_tasks']
    if child_tasks:
        for task_name in child_tasks:
            create_task(task_name, task)
    task.started = now()
    task.save()


def get_postponed_tasks() -> List[SystemTask]:
    query_set = SystemTask.objects.filter(started__isnull=False)
    query_set = query_set.filter(done__isnull=True)
    query_set = query_set.filter(postponed__isnull=False)
    return query_set


def trigger_postponed_task(task: List[SystemTask]):
    pass


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        while True:
            # Validate completed tasks and process all (once a second)
            done_tasks = get_done_network_tasks()
            # Once a minute do search for tasks with all completed children
            # done_tasks.extend(search_tasks_with_completed_child())
            # Collect list of tasks that has completed children
            # Validate parent tasks whether they has all child tasks completed and do post processing
            # tasks_may_be_done = {finalize_task(task) for task in done_tasks}
            # At this stage done from child task each time task is done
            for task in done_tasks:
                finalize_task(task)
            # Get not-started tasks and init preprocessing for all
            new_tasks = get_new_tasks()
            for task in new_tasks:
                start_task(task)
            # Validate postponed tasks and init processing for all
            postponed_tasks = get_postponed_tasks()
            for task in postponed_tasks:
                trigger_postponed_task(task)
            print('Cycle done')
            sleep(1)
            # If no events occurred - idle for 5 seconds
        self.stdout.write(self.style.SUCCESS('done'))
