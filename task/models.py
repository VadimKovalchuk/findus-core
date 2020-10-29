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
    priority = models.IntegerField(choices=Priorities.choices)
    module = models.CharField(max_length=100)
    function = models.CharField(max_length=100)
    arguments = models.TextField(null=True)

