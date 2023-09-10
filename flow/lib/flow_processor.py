import logging

from datetime import timedelta
from typing import Union

from django.utils.timezone import now

from flow.models import Flow, FlowState
from task.lib.constants import FLOW_PROCESSING_QUOTAS
from lib.db import DatabaseMixin, get_created_flows, get_running_flows, get_postponed_flows, generic_query_set_generator
from lib.common_service import CommonServiceMixin
from task.models import SystemTask, NetworkTask, TaskState

logger = logging.getLogger('flow_processor')


class FlowProcessor(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queues = {
                FlowState.CREATED: generic_query_set_generator(get_created_flows),
                FlowState.RUNNING: generic_query_set_generator(get_running_flows),
                FlowState.POSTPONED: generic_query_set_generator(get_postponed_flows),
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
