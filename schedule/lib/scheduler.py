import logging
from lib.common_service import CommonServiceMixin
from lib.db import DatabaseMixin, generic_query_set_generator
from schedule.models import Event, Schedule

from django.db.models.query import QuerySet
from django.utils.timezone import now

logger = logging.getLogger('scheduler')


def get_pending_schedules(schedule: Schedule) -> QuerySet:
    query_set = schedule.objects.filter(next_trigger__lt=now())
    return query_set


class ScheduleProcessor(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queue = generic_query_set_generator(get_pending_schedules, Schedule)

    @staticmethod
    def clone(event: Event):
        return Event.objects.create(
            name=event.name,
            type=event.type,
            artifacts=event.artifacts,
            tasks=event.tasks
        )

    def processing_cycle(self):
        for schedule in self.queue:
            if not schedule:
                break
            logger.debug(schedule.__dict__)
            # Trigger schedule related event
            event: Event = schedule.event
            logger.debug(f'Triggering event: {event}')
            event.trigger()
            event.triggered = now()  # Marking event as triggered
            event.save()
            if schedule.cron:  # if event is periodic
                schedule.calculate_next_trigger()
                schedule.save()
                # Scheduling nex identical event with issued crone
                next_event = self.clone(event)
                next_event.save()
                for event_related_schedule in event.get_schedule():
                    event_related_schedule.event = next_event
                    event_related_schedule.save()
            else:
                schedule.delete()
            self.idle = False
