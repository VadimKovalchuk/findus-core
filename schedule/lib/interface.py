from schedule.models import Schedule, Event


class Scheduler:
    def __init__(self, event_name: str, artifacts: str):
        self.event: Event = Event.objects.create(name=event_name, artifacts=artifacts)
        self.schedule: Schedule = Schedule.objects.create(event=self.event)

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
    def tasks(self):
        return self.event.tasks

    @tasks.setter
    def tasks(self, value):
        self.event.tasks = value

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
