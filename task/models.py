import json

from datetime import datetime, timedelta
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
    sent = models.DateTimeField(null=True)
    priority = models.IntegerField(choices=Priorities.choices, default=Priorities.MEDIUM)
    flow = models.ForeignKey('flow.Flow', null=True, on_delete=models.CASCADE)
    arguments = models.TextField(default='{}')
    module = models.CharField(max_length=100)
    function = models.CharField(max_length=100)
    result = models.TextField(default='{}')

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

    @property
    def postponed_relative(self):
        if self.postponed:
            return self.postponed - datetime.now()
        else:
            return timedelta(seconds=0)

    @postponed_relative.setter
    def postponed_relative(self, delta: timedelta):
        self.postponed = now() + delta

    def compose_for_dcn(self, client: str = ''):
        return {
            'id': self.id,
            'client': client,
            'module': self.module,
            'function': self.function,
            'arguments': self.arguments_dict
        }

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
