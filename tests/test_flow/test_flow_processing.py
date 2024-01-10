import logging

from time import monotonic, sleep

import pytest

from django.utils.timezone import now

from flow.lib.flow_processor import FlowProcessor
from flow.models import FlowState
from flow.workflow import TestRelayWorklow, TestStagesWorklow
from task.models import Task

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def test_flow_start():
    flow_processor = FlowProcessor()
    workflow = TestRelayWorklow()
    flow = workflow.create()
    flow_processor.generic_stage_handler(flow_processor.start_flow, FlowState.CREATED)
    flow.refresh_from_db()
    logger.debug(flow.state)
    assert flow == next(flow_processor.queues[FlowState.RUNNING]), \
        'Started flow is missing in started tasks queue'
    assert not next(flow_processor.queues[FlowState.CREATED]), \
        'Unexpected flow is received from created tasks queue'


def test_task_creation():
    flow_processor = FlowProcessor()
    workflow = TestRelayWorklow()
    flow = workflow.create()
    assert len(flow.tasks) == 0, 'Task exist when not expected'
    flow_processor.generic_stage_handler(flow_processor.start_flow, FlowState.CREATED)
    flow.refresh_from_db()
    assert len(flow.tasks) == 1, 'Task is not created when expected'
    for task in flow.tasks:
        assert isinstance(task, Task), 'Child task type mismatch'
        assert task.name == 'network_relay_task', 'Child task name mismatch'


def test_task_lifecycle():
    flow_processor = FlowProcessor()
    workflow = TestStagesWorklow()
    flow = workflow.create()
    start = monotonic()
    while not flow.processing_state == FlowState.DONE and monotonic() < start + 5:
        flow_processor.processing_cycle()
        flow.refresh_from_db()
        logger.debug(flow.processing_state)
    logger.info(monotonic() - start)


def test_flow_finalization():
    flow_processor = FlowProcessor()
    workflow = TestStagesWorklow()
    flow = workflow.create()
    flow.state = FlowState.RUNNING
    flow.stage = workflow.stage_count - 1
    flow.save()
    flow_processor.generic_stage_handler(flow_processor.process_flow, FlowState.RUNNING)
    flow.refresh_from_db()
    logger.info((flow.state, flow.processing_state, flow.postponed))

    assert not next(flow_processor.queues[FlowState.RUNNING]), \
        'Unexpected flow is received from running queue'
    assert not next(flow_processor.queues[FlowState.POSTPONED]), \
        'Unexpected flow is received from postponed queue'

    flow.postponed = now()
    flow.save()
    logger.info((flow.state, flow.processing_state, flow.postponed))

    assert flow == next(flow_processor.queues[FlowState.POSTPONED]), \
        'Completed flow is missing in postponed queue'

    flow_processor.generic_stage_handler(flow_processor.cancel_postpone, FlowState.POSTPONED)
    flow.refresh_from_db()
    logger.info((flow.state, flow.processing_state, flow.postponed))

    assert flow == next(flow_processor.queues[FlowState.DONE]), \
        'Completed flow is missing in completed queue'
    assert not next(flow_processor.queues[FlowState.POSTPONED]), \
        'Unexpected flow is received from postponed queue'

    flow_processor.generic_stage_handler(flow_processor.cleanup_done, FlowState.DONE)
    assert not next(flow_processor.queues[FlowState.DONE]), \
        'Unexpected flow is received from completed queue'


def test_task_post_processing():
    pass