from datetime import datetime
from typing import List

from schedule.lib.event_templates import get_event_template
from flow.models import Flow

from croniter import croniter
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
    triggered = models.DateTimeField(null=True)
    artifacts = models.TextField(null=True)
    tasks = models.TextField(null=True)

    def get_template(self):
        return get_event_template(self.name)

    def tasks_from_template(self):
        template = self.get_template()
        task_list = template.get('commands', [])
        self.tasks = ','.join(task_list)

    def get_schedule(self):
        return list(self.schedule_set.all())

    def get_flows(self) -> List[Flow]:
        return self.flow_set.all()

    def __str__(self):
        return f'({self.id}) "{self.name}": {self.artifacts}'


class Schedule(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    next_trigger = models.DateTimeField(auto_now_add=True)
    cron = models.CharField(max_length=20, null=True)

    def get_cron_iterator(self):
        if self.cron:
            base = datetime.now()
            return croniter(self.cron, base)

    def calculate_next_trigger(self):
        if self.cron:
            self.next_trigger = self.get_cron_iterator().get_next(datetime)
            return self.next_trigger
