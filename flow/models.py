import json

from datetime import datetime, timedelta
from typing import List

from django.db import models
from django.utils.timezone import now


class Flow(models.Model):

    class Priorities(models.IntegerChoices):
        BLOCKING = 0
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    id = models.AutoField(primary_key=True, help_text='Internal ID')
    name = models.CharField(max_length=100)
    step = models.IntegerField(default=0)
    postponed = models.DateTimeField(null=True)
    priority = models.IntegerField(choices=Priorities.choices, default=Priorities.MEDIUM)
    arguments = models.TextField(null=True)

    @property
    def arguments_dict(self):
        return json.loads(self.arguments)

    @arguments_dict.setter
    def arguments_dict(self, _dict: dict):
        self.arguments = json.dumps(_dict)
