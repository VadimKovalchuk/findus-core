import logging

from schedule.models import Schedule, Event


logger = logging.getLogger('scheduler')


class Scheduler:
    def __init__(self, event_name: str, artifacts: str):
        self.event: Event = Event.objects.create(name=event_name, artifacts=artifacts)
        self.event.workflows_from_template()
        self.schedule: Schedule = Schedule.objects.create(event=self.event)
        logger.info(f'Event created: {self.event}. Next trigger: {self.schedule.next_trigger}')

    @property
    def type(self):
        return self.event.type

    @type.setter
    def type(self, value):
        self.event.type = value

    @property
    def artifacts(self):
        return self.event.artifacts

    @artifacts.setter
    def artifacts(self, value):
        self.event.artifacts = value

    @property
    def workflows(self):
        return self.event.workflows

    @workflows.setter
    def workflows(self, value):
        self.event.workflows = value

    @property
    def trigger_datetime(self):
        return self.schedule.next_trigger

    @trigger_datetime.setter
    def trigger_datetime(self, value):
        self.schedule.next_trigger = value

    @property
    def cron(self):
        return self.schedule.cron

    @cron.setter
    def cron(self, value):
        self.schedule.cron = value
        self.schedule.next_trigger = self.schedule.calculate_next_trigger()

    def push(self):
        self.event.save()
        self.schedule.save()
