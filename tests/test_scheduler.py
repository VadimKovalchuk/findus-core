import logging

from copy import deepcopy
from datetime import datetime, timedelta

import croniter
import pytest

from django.utils.timezone import now

from schedule.lib.interface import Scheduler
from schedule.lib.scheduler import ScheduleProcessor
from schedule.models import Event, Schedule
from task.lib.commands import COMMANDS, Command


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
        'Description mismatch'
    assert ','.join(template.get('workflows')) == event_scheduler.event.workflows, \
        'workflows are not reapplied from template'


def test_trigger_single_event():
    processor = ScheduleProcessor()
    event_scheduler = Scheduler('name', SAMPLE_TICKER)
    event_scheduler.push()
    event: Event = event_scheduler.event
    processor.processing_cycle()
    event.refresh_from_db()
    assert event.triggered, "Triggered event has corresponding parameter content empty"
    assert not event.get_schedule(), "Triggered event has schedule object preserved"


def test_trigger_periodic_event():
    base = datetime.now()
    cron = '1 * * * *'
    processor = ScheduleProcessor()
    event_scheduler = Scheduler('name', SAMPLE_TICKER)
    event_scheduler.cron = cron
    event_scheduler.trigger_datetime = now()
    event_scheduler.push()
    event: Event = event_scheduler.event
    schedule: Schedule = event_scheduler.schedule
    processor.processing_cycle()
    event.refresh_from_db()
    schedule.refresh_from_db()
    assert event.triggered, "Triggered event has corresponding parameter content empty"
    assert not event.get_schedule(), "Triggered event has schedule object preserved"
    assert event != schedule.event, "Cron schedule is linked to previous event after trigger"
    assert schedule.next_trigger == croniter.croniter(cron, base).get_next(datetime), \
        "Next trigger datetime is not calculated for cron schedule"


def test_trigger_event_with_workflow():
    processor = ScheduleProcessor()
    event_scheduler = Scheduler('name', SAMPLE_TICKER)
    event_scheduler.tasks = 'system_relay_task'
    event_scheduler.push()
    event: Event = event_scheduler.event
    processor.processing_cycle()
    event.refresh_from_db()
    logger.debug(event.workflows)
    assert event.flows, "Triggered event with workflows has related flows property empty"
    assert event.flows[0].name == 'test_stages', "Triggered event child task name mismatch"


def test_event_without_template():
    event_scheduler = Scheduler('random', 'artifactless')
    event_scheduler.push()
    assert Event.objects.all(), 'Event without template is not created'


def test_task_wrapping_function_failure():
    assert False, 'Not implemented'
    command: Command = deepcopy(COMMANDS['system_relay_task'])
    command.run_on_start = ['failing']
    system_task = command.create_task()
    command.on_start(system_task)
    events = Event.objects.all()
    assert events, 'Wrapping function failure is not followed by Event creation'
    event = events[0]
    assert 'failing' in event.name, 'Wrapping func failure Event is not descriptive'
