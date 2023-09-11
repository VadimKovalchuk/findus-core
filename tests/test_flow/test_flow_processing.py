import logging

import pytest

from flow.lib.flow_processor import FlowProcessor
from flow.models import FlowState
from flow.workflow.test import TestRelayFlow
from flow.workflow import get_classes

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def _test_flow_start():
    flow_processor = FlowProcessor()
    # cmd: Command = COMMANDS[task_name]
    # task = cmd.create_task()
    workflow = TestRelayFlow()
    flow = workflow.create()
    flow_processor.generic_stage_handler(flow_processor.start_flow, FlowState.CREATED)
    flow_processor.generic_stage_handler(flow_processor.start_flow, FlowState.CREATED)
    flow.refresh_from_db()
    logger.debug(flow.state)
    assert flow == next(flow_processor.queues[FlowState.RUNNING]), \
        'Started flow is missing in started tasks queue'
    assert not next(flow_processor.queues[FlowState.CREATED]), \
        'Unexpected flow is received from created tasks queue'

def test_foo():
    logger.info(f'CLASSES: {get_classes()}')