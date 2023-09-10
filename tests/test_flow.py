import logging

from typing import Generator

import pytest

from flow.lib.flow_processor import FlowProcessor
from flow.models import Flow, FlowState
from flow.flows.test.test import TestRelayFlow

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def validate_flow_queue(flow: Flow, expected_queue: Generator, flow_proc: FlowProcessor):
    for queue_name, queue in flow_proc.queues.items():
        received_task = next(queue)
        if queue == expected_queue:
            assert received_task == flow, \
                f'Flow with state "{flow.state}" is missing in corresponding queue: {queue_name}'
        else:
            assert not received_task, \
                f'Flow with state "{flow.state}" is received from unexpected queue: {queue_name}'


def test_flow_queues():
    def validate_flow_in_queue(state: str):
        assert flow.state == state, 'Flow state validation failure'
        flow_from_queue = next(flow_processor.queues[state])
        assert flow_from_queue == flow, 'Flow does not corresponds to expected one'
        validate_flow_queue(flow, flow_processor.queues[state], flow_processor)
    flow_processor = FlowProcessor()
    #cmd: Command = COMMANDS[task_name]
    # Created task
    #task = cmd.create_task()
    flow = TestRelayFlow(name='TestRelayFlow')
    validate_flow_in_queue(FlowState.CREATED)
    # Run flow
    flow.state = FlowState.RUNNING
    flow.save()
    validate_flow_in_queue(FlowState.RUNNING)
    # Done task
    flow.state = FlowState.DONE
    flow.save()
    validate_flow_in_queue(FlowState.DONE)
