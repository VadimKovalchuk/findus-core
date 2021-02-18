import json

from django.db import models


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
    priority = models.IntegerField(choices=Priorities.choices,
                                   default=Priorities.MEDIUM)
    module = models.CharField(max_length=100)
    function = models.CharField(max_length=100)
    arguments = models.TextField(null=True)
    result = models.TextField(null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f'({self.id}) "{self.name}"'


class SystemTask(Task):
    child_tasks = models.ManyToManyField('self', related_name='parent_tasks')
    network_tasks = models.ManyToManyField('NetworkTask', related_name='parent_system_tasks')


class NetworkTask(Task):

    def compose_for_dcn(self):
        return {
            'id': self.id,
            'client': '',
            'module': self.module,
            'function': self.function,
            'arguments': json.loads(self.arguments) if (self.arguments and '{' in self.arguments) else self.arguments
        }
