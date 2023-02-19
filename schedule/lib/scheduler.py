from lib.common_service import CommonServiceMixin
from lib.db import DatabaseMixin
from schedule.models import Schedule

def get_pending_schedules() -> QuerySet:
    query_set = Schedule.objects.filter(postponed__lt=now())
    return query_set

class SchedulerEngine(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queue = get_pending_schedules()
