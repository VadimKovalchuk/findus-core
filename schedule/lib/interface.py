from schedule.models import Schedule, Event


class Scheduler:
    def __init__(self, event_name: str, artifacts: str):
        self._event = Event(name=event_name, artifacts=artifacts)
        self._schedule = Schedule(event=self._event)

    @property
    def type(self):
        return self._event.type

    @type.setter
    def type(self, value):
        self._event.type = value

    @property
    def artifacts(self):
        return self._event.artifacts

    @artifacts.setter
    def artifacts(self, value):
        self._event.artifacts = value

    @property
    def commands(self):
        return self._event.commands

    @commands.setter
    def commands(self, value):
        self._event.commands = value

    @property
    def trigger_datetime(self):
        return self._schedule.next_trigger

    @trigger_datetime.setter
    def trigger_datetime(self, value):
        self._schedule.next_trigger = value

    @property
    def cron(self):
        return self._schedule.cron

    @cron.setter
    def cron(self, value):
        self._schedule.cron = value
        self._schedule.next_trigger = self._schedule.calculate_next_trigger()

    def push(self):
        self._event.save()
        self._schedule.save()


class SchedulerEngine:
    pass
