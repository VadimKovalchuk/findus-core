import logging
from datetime import datetime
from time import sleep

from task.commands import commands
from django.core.management.base import BaseCommand, CommandError
from task.models import NetworkTask, SystemTask

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
        task.save()
        if isinstance(task, SystemTask):
            parent_task.child_tasks.add(task)
        else:
            parent_task.network_tasks.add(task)
        parent_task.save()
        print(parent_task.child_tasks.all(), parent_task.network_tasks.all())
    print(task)


class TaskProcessor:

    def __init__(self, task: SystemTask):
        self.task = task
        if not task.started and not task.done:
            self.on_create()
        elif task.done:
            self.on_done()

    def on_create(self):
        child_tasks = commands[self.task.name]['child_tasks']
        if child_tasks:
            for task_name in child_tasks:
                create_task(task_name, self.task)
        self.task.created = datetime.now()

    def in_progress(self):
        pass

    def on_done(self):
        pass


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        self.stdout.write(f'Tasks: {len(SystemTask.objects.all())}')
        for task in SystemTask.objects.all():
            self.stdout.write(f'Got task: {task.name}')
            TaskProcessor(task)

        self.stdout.write(self.style.SUCCESS('done'))
