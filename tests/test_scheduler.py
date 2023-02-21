import logging

from datetime import datetime, timedelta

from schedule.lib.interface import Scheduler
from schedule.lib.scheduler import ScheduleProcessor
from schedule.models import Event, Schedule

import pytest


pytestmark = pytest.mark.django_db
logger = logging.getLogger(__name__)

SAMPLE_TICKER = 'MSFT'


def test_instant_event_creation():
    create_time = datetime.now()
    event_scheduler = Scheduler('name', SAMPLE_TICKER)
    event_scheduler.push()
    event_time = event_scheduler.trigger_datetime
    logger.debug(f'create = {create_time}, actual = {event_time}')
    assert create_time < event_time < create_time + timedelta(seconds=1), \
        f'Scheduled event time ({event_time}) severally differs from the invocation time ({create_time})'
    assert not event_scheduler.event.triggered, 'New event has "created" time triggered without processing'


def test_schedule_correspondence():
    event_scheduler = Scheduler('name', SAMPLE_TICKER)
    event_scheduler.push()
    created_schedule: Schedule = event_scheduler.schedule
    ref_schedule: Schedule = event_scheduler.event.get_schedule()[0]
    assert created_schedule == ref_schedule, 'Created event does not correspond to referenced one'


def test_event_template():
    event_scheduler = Scheduler('name', SAMPLE_TICKER)
    template: dict = event_scheduler.event.get_template()
    logger.debug(template)
    assert template.get('human_name') == "base event", f'Human readable name mismatch'
    assert template.get('description') == "base event example", \
        f'Description mismatch'


def test_trigger_single_event():
    processor = ScheduleProcessor()
    event_scheduler = Scheduler('name', SAMPLE_TICKER)
    event_scheduler.push()
    event: Event = event_scheduler.event
    processor.processing_cycle()
    event.refresh_from_db()
    assert event.triggered, "Triggered event has corresponding parameter content empty"
    assert not event.get_schedule(), "Triggered event has schedule object preserved"
