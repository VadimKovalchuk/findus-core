import logging

from datetime import timedelta
from typing import Union

from django.utils.timezone import now

from flow.models import Flow, FlowState
from task.lib.constants import FLOW_PROCESSING_QUOTAS
from lib.db import DatabaseMixin, created_flows, running_flows, postponed_flows
from lib.common_service import CommonServiceMixin
from task.models import SystemTask, NetworkTask, TaskState

logger = logging.getLogger(__name__)


class FlowProcessor(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queues = {
                FlowState.CREATED: created_flows,
                FlowState.RUNNING: running_flows,
                FlowState.POSTPONED: postponed_flows,
            }
        self.quotas = FLOW_PROCESSING_QUOTAS
        self.stages = (
            (self.start_flow, FlowState.CREATED),
            (self.process_flow, FlowState.RUNNING),
            (self.cancel_postpone, FlowState.POSTPONED),
        )

    def start_flow(self, flow: Flow):
        logger.info(f'Starting flow: {flow}')

    def process_flow(self, flow: Flow):
        logger.info(f'Processing flow: {flow}')

    def cancel_postpone(self, flow: Flow):
        flow.postponed = None
        flow.save()

    def processing_cycle(self):
        for stage_handler, task_state in self.stages:
            self.generic_stage_handler(stage_handler, task_state)
