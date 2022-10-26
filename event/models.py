from typing import List

from task.models import SystemTask

from django.db import models


class Event(models.Model):

    class UserType(models.IntegerChoices):
        SYSTEM = 0
        ADMIN = 1
        ELITE = 2
        REGULAR = 3

    id = models.AutoField(primary_key=True, help_text='Internal ID')
    name = models.CharField(max_length=100)
    type = models.IntegerField(choices=UserType.choices, default=UserType.REGULAR)
    created = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    artifacts = models.TextField(null=True)
    manual_commands = models.TextField(null=True)
    auto_commands = models.TextField(null=True)

    def create_task(self, command):
        task: SystemTask = SystemTask.objects.create(name=command)
        task.event = self
        task.arguments = self.artifacts
        task.save()
        return task

    def trigger_auto_commands(self):
        for command in self.manual_commands.split(','):
            self.create_task(command)

    def get_tasks(self) -> List[SystemTask]:
        return self.systemtask_set.all()

    def __str__(self):
        return f'({self.id}) "{self.name}": {self.artifacts}'
