import json

from typing import List

from django.db import models
from django.utils.timezone import now


class TaskState:
    CREATED = 'created'
    STARTED = 'started'
    PROCESSED = 'processed'
    DONE = 'done'
    POSTPONED = 'postponed'
    UNDEFINED = 'undefined'
    STATES = [CREATED, STARTED, PROCESSED, DONE, POSTPONED, UNDEFINED]


class Task(models.Model):

    class Priorities(models.IntegerChoices):
        BLOCKING = 0
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    id = models.AutoField(primary_key=True, help_text='Internal ID')
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    postponed = models.DateTimeField(null=True)
    started = models.DateTimeField(null=True)
    done = models.DateTimeField(null=True)
    processed = models.DateTimeField(null=True)
    priority = models.IntegerField(choices=Priorities.choices,
                                   default=Priorities.MEDIUM)
    parent_task = models.ForeignKey('SystemTask', null=True, on_delete=models.CASCADE)
    module = models.CharField(max_length=100)
    function = models.CharField(max_length=100)
    arguments = models.TextField(null=True)
    result = models.TextField(null=True)

    class Meta:
        abstract = True

    @property
    def state(self):
        if self.postponed:
            return TaskState.POSTPONED
        elif self.created and not any((self.started, self.processed, self.done)):
            return TaskState.CREATED
        elif all((self.created, self.started)) and not any((self.processed, self.done)):
            return TaskState.STARTED
        elif all((self.created, self.started, self.processed)) and not self.done:
            return TaskState.PROCESSED
        elif all((self.created, self.started, self.processed, self.done)):
            return TaskState.DONE
        else:
            # TODO: Report Event to DB
            return TaskState.UNDEFINED

    def _stats(self):
        return {
            'created': 1 if (self.created and not self.started) else 0,
            'started': 1 if (self.started and not self.done) else 0,
            'done': 1 if (self.done and not self.processed) else 0,
            'processed': 1 if self.processed else 0
        }

    def __str__(self):
        return f'({self.id}) "{self.name}"'


class SystemTask(Task):

    def get_children(self) -> List[Task]:
        children = list()
        children.extend(self.systemtask_set.all())
        children.extend(self.networktask_set.all())
        return children

    def child_stats(self) -> dict:
        result_stats = self._stats()
        children = self.get_children()
        for task in children:
            if isinstance(task, SystemTask):
                stats = task.child_stats()
            elif isinstance(task, NetworkTask):
                stats = task._stats()
            else:
                raise TypeError
            for key in stats:
                result_stats[key] += stats[key]
        return result_stats

    def is_done(self) -> bool:
        children = self.get_children()
        lst_cmp = [task.processed for task in children]
        if all(lst_cmp):
            if not self.done:
                self.done = now()
                self.save()
            print(f'{self} is done')
            return True
        else:
            return False


class NetworkTask(Task):

    def compose_for_dcn(self, client: str = ''):
        return {
            'id': self.id,
            'client': client,
            'module': self.module,
            'function': self.function,
            'arguments': json.loads(self.arguments) if (self.arguments and '{' in self.arguments) else self.arguments
        }
