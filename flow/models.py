import json

from datetime import datetime, timedelta
from typing import List

from django.db import models
from django.utils.timezone import now

from task.models import NetworkTask


class FlowState:
    CREATED = 'created'
    RUNNING = 'running'
    DONE = 'done'
    POSTPONED = 'postponed'
    states = [CREATED, RUNNING, DONE]
    choices = ((state, state) for state in states)


class Flow(models.Model):

    class Priorities(models.IntegerChoices):
        BLOCKING = 0
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    id = models.AutoField(primary_key=True, help_text='Internal ID')
    name = models.CharField(max_length=100)
    stage = models.IntegerField(default=0)
    event = models.ForeignKey('schedule.Event', null=True, on_delete=models.CASCADE)
    processing_state = models.CharField(max_length=10, choices=FlowState.choices, default=FlowState.CREATED)
    arguments = models.TextField(default='{}')
    postponed = models.DateTimeField(null=True)
    priority = models.IntegerField(choices=Priorities.choices, default=Priorities.MEDIUM)

    @property
    def state(self):
        if self.postponed:
            return FlowState.POSTPONED
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
    def tasks(self) -> NetworkTask:
        return self.networktask_set.all()
