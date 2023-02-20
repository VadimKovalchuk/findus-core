from lib.common_service import CommonServiceMixin
from lib.db import DatabaseMixin
from schedule.models import Event, Schedule

from django.db.models.query import QuerySet
from django.utils.timezone import now


def get_pending_schedules() -> QuerySet:
    query_set = Schedule.objects.filter(next_trigger__lt=now())
    return query_set


class SchedulerEngine(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queue = get_pending_schedules()

    def clone(self, event: Event):
        return Event.objects.create(
            name=event.name,
            type=event.type,
            artifacts=event.artifacts,
            tasks=event.tasks
        )

    def processing_cycle(self):
        for schedule in self.queue:
            # Trigger schedule related event
            event: Event = schedule.event
            event.trigger()
            event.triggered = now()  # Marking event as triggered
            if schedule.cron:  # if event is periodic
                schedule.calculate_next_trigger()
                # Scheduling nex identical event with issued crone
                next_event = self.clone(event)
                for event_related_schedule in event.get_schedule():
                    event_related_schedule.event = next_event
            else:
                schedule.delete()
