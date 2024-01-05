import logging

from datetime import timedelta

from django.utils.timezone import now

from flow.models import Flow, FlowState
from flow.workflow import get_workflow_map
from task.lib.constants import FLOW_PROCESSING_QUOTAS
from lib.db import (DatabaseMixin, get_created_flows, get_done_flows, get_running_flows,
                    get_postponed_flows, generic_query_set_generator)
from lib.common_service import CommonServiceMixin

logger = logging.getLogger('flow_processor')


class FlowProcessor(CommonServiceMixin, DatabaseMixin):
    def __init__(self):
        CommonServiceMixin.__init__(self)
        self.queues = {
                FlowState.CREATED: generic_query_set_generator(get_created_flows),
                FlowState.RUNNING: generic_query_set_generator(get_running_flows),
                FlowState.POSTPONED: generic_query_set_generator(get_postponed_flows),
                FlowState.DONE: generic_query_set_generator(get_done_flows),
            }
        self.stages = (
            (self.start_flow, FlowState.CREATED),
            (self.process_flow, FlowState.RUNNING),
            (self.cancel_postpone, FlowState.POSTPONED),
            (self.cleanup_done, FlowState.DONE),
        )
        self.quotas = FLOW_PROCESSING_QUOTAS
        self.workflow_map = get_workflow_map()

    def start_flow(self, flow: Flow):
        logger.info(f'Starting flow: {flow.name}')
        start_result = self.process_flow(flow)
        if start_result:
            flow.state = FlowState.RUNNING
            flow.save()
        return start_result

    def process_flow(self, flow: Flow):
        logger.info(f'Processing flow: ({flow.id}){flow.name}')
        workflow = self.workflow_map[flow.name](flow)
        active_stage = workflow.get_active_stage_method()
        processing_result = active_stage()
        if processing_result:
            if workflow.check_last_stage():
                flow.state = FlowState.DONE
                flow.postponed = now() + timedelta(days=92)
            else:
                flow.stage += 1
            flow.save()
        return processing_result

    def cancel_postpone(self, flow: Flow):
        flow.postponed = None
        flow.save()
        return True

    def cleanup_done(self, flow: Flow):
        flow.delete()
        return True

    def processing_cycle(self):
        for stage_handler, task_state in self.stages:
            self.generic_stage_handler(stage_handler, task_state)
