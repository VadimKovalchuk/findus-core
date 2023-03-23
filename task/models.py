import json

from typing import List

from django.db import models


class TaskState:
    CREATED = 'created'
    STARTED = 'started'
    PROCESSED = 'processed'
    DONE = 'done'
    POSTPONED = 'postponed'
    UNDEFINED = 'undefined'
    states = [CREATED, STARTED, PROCESSED, DONE, POSTPONED]
    choices = ((state, state) for state in states)


class Task(models.Model):

    class Priorities(models.IntegerChoices):
        BLOCKING = 0
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    id = models.AutoField(primary_key=True, help_text='Internal ID')
    name = models.CharField(max_length=100)
    processing_state = models.CharField(max_length=10, choices=TaskState.choices, default=TaskState.CREATED)
    postponed = models.DateTimeField(null=True)
    priority = models.IntegerField(choices=Priorities.choices, default=Priorities.MEDIUM)
    parent_task = models.ForeignKey('SystemTask', null=True, on_delete=models.CASCADE)
    arguments = models.TextField(null=True)
    result = models.TextField(null=True)

    class Meta:
        abstract = True

    @property
    def state(self):
        if self.postponed:
            return TaskState.POSTPONED
        else:
            return self.processing_state

    @state.setter
    def state(self, state: str):
        self.processing_state = state

    @property
    def arguments_dict(self):
        return json.loads(self.arguments)

    @arguments_dict.setter
    def arguments_dict(self, _dict: dict):
        self.arguments = json.dumps(_dict)

    @property
    def result_dict(self):
        if self.result:
            return json.loads(self.result)
        else:
            return dict()

    @result_dict.setter
    def result_dict(self, _dict: dict):
        self.result = json.dumps(_dict)

    def _stats(self):
        return {
            TaskState.CREATED: 1 if self.state == TaskState.CREATED else 0,
            TaskState.STARTED: 1 if self.state == TaskState.STARTED else 0,
            TaskState.PROCESSED: 1 if self.state == TaskState.PROCESSED else 0,
            TaskState.DONE: 1 if self.state == TaskState.DONE else 0,
            TaskState.POSTPONED: 1 if self.state == TaskState.POSTPONED else 0,
        }

    def __str__(self):
        return f'({self.id}) "{self.name}"'


class SystemTask(Task):

    event = models.ForeignKey('schedule.Event', null=True, on_delete=models.CASCADE)

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

    def is_processed(self) -> bool:
        children = self.get_children()
        processed = [task.state == TaskState.DONE for task in children]
        return all(processed)


class NetworkTask(Task):

    sent = models.DateTimeField(null=True)
    module = models.CharField(max_length=100)
    function = models.CharField(max_length=100)

    def compose_for_dcn(self, client: str = ''):
        return {
            'id': self.id,
            'client': client,
            'module': self.module,
            'function': self.function,
            'arguments': self.arguments_dict
        }
