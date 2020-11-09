from datetime import datetime

from django.db import models


class Task(models.Model):

    class Priorities(models.IntegerChoices):
        BLOCKING = 0
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    id = models.AutoField(primary_key=True, help_text='Internal ID')
    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True)
    priority = models.IntegerField(choices=Priorities.choices,
                                   default=Priorities.MEDIUM)
    module = models.CharField(max_length=100)
    function = models.CharField(max_length=100)
    arguments = models.TextField(null=True)

    def compose_for_dcn(self):
        return {
            'id': self.id,
            'client': {},
            'module': self.module,
            'function': self.function,
            'arguments': self.arguments
        }

    def __str__(self):
        return f'Task({self.id}): {self.module}.{self.function} for [ticker]'
