import json
import logging

from datetime import timedelta

from django.utils.timezone import now

from flow.models import Flow, FlowState
from flow.workflow import get_workflow_map
from task.lib.constants import FLOW_PROCESSING_QUOTAS
from lib.db import (DatabaseMixin, get_created_flows, get_done_flows, get_running_flows,
                    get_postponed_flows, generic_query_set_generator)
from lib.common_service import CommonServiceMixin
from schedule.lib.interface import Scheduler

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
        logger.info(f'Processing flow: ({flow.id}){flow.name} stage {flow.stage}')
        workflow = self.workflow_map[flow.name](flow)
        active_stage = workflow.get_active_stage_method()
        #logger.debug(active_stage)
        try:
            processing_result = active_stage()
        except Exception:
            processing_result = False
            logger.error(f'Flow "{flow.name}" has failed with exception on stage "{active_stage.__name__}"')
            scheduler: Scheduler = Scheduler(event_name='flow_failure', artifacts=json.dumps({"flow": flow.id}))
            scheduler.push()
            flow.postponed = now() + timedelta(hours=1)
        if processing_result:
            if workflow.check_last_stage():
                workflow.set_done()
            else:
                flow.stage += 1
        # else:
        #     logger.error(f'Flow "{flow.name}" has failed on stage "{active_stage.__name__}"')
        #     scheduler: Scheduler = Scheduler(event_name='flow_failure', artifacts=json.dumps({"flow": flow.id}))
        #     scheduler.push()
        #     flow.postponed = now() + timedelta(days=92)
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
        for stage_handler, flow_state in self.stages:
            self.generic_stage_handler(stage_handler, flow_state)
