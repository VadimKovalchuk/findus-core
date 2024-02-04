import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Iterable

from django.db.models import Q

from django.utils.timezone import now


from flow.models import Flow, FlowState
from flow.workflow.constants import STAGE_COUNT_CAP, REQUEUE_PERIOD
from task.models import Task, TaskState


logger = logging.getLogger('flow_processor')


class Workflow:
    flow_name = 'generic'
    _default_requeue_period = 1  # minute

    def __init__(self, flow: Flow = None):
        self.flow = flow

    @property
    def stage_count(self):
        max_stage = 0
        for stage_id in range(STAGE_COUNT_CAP + 1):
            try:
                if getattr(self, f'stage_{stage_id}'):
                    max_stage += 1
            except AttributeError:
                return max_stage

    @property
    def stage(self):
        return self.flow.stage

    @stage.setter
    def stage(self, stage: str):
        self.flow.stage = stage
        self.flow.save()

    @property
    def state(self):
        return self.flow.state

    @state.setter
    def state(self, state: str):
        self.flow.state = state
        self.flow.save()

    @property
    def processing_state(self):
        return self.flow.processing_state

    @property
    def postponed(self):
        return self.flow.postponed

    @postponed.setter
    def postponed(self, date: datetime):
        self.flow.postponed = date
        self.flow.save()

    @property
    def arguments(self):
        return self.flow.arguments_dict

    @arguments.setter
    def arguments(self, _dict: Dict):
        self.flow.arguments_dict = _dict
        self.flow.save()

    def refresh_from_db(self):
        self.flow.refresh_from_db()

    def save(self):
        self.flow.save()

    def set_done(self):
        self.flow.set_done()

    def update_arguments(self, _dict: Dict):
        arguments: Dict = self.arguments
        arguments.update(_dict)
        self.arguments = arguments
        self.save()

    def check_last_stage(self):
        return self.stage_count == self.stage + 1

    def get_active_stage_method(self):
        if self.flow.stage > self.stage_count:
            raise AttributeError('Flow active stage is more than total stage count')
        return getattr(self, f'stage_{self.flow.stage}')

    def create(self):
        self.flow = Flow.objects.create(name=self.flow_name)
        return self.flow

    def stage_0(self):
        return True

    def set_for_test(self):
        pass

    def postpone_requeue(self):
        requeue_period = self.arguments.get(REQUEUE_PERIOD, self._default_requeue_period)
        self.postponed = now() + timedelta(minutes=requeue_period)
        self.save()


class TaskHandler:

    @property
    def tasks(self) -> List[Task]:
        return self.flow.task_set.all()

    @property
    def undone_tasks(self) -> List[Task]:
        return self.flow.task_set.filter(~Q(processing_state=TaskState.DONE))

    def distribute_task_on_timeline(self, start_delay: int, step: int):
        delay = start_delay
        for task in self.undone_tasks:
            task.postponed = now() + timedelta(seconds=delay)
            delay += step

    def check_all_task_processed(self):
        processed = self.flow.task_set.filter(processing_state=TaskState.PROCESSED)
        # print((len(processed), len(self.undone_tasks)))
        # print(len(processed) == len(self.undone_tasks))
        return len(processed) == len(self.undone_tasks)

    def map_task_results(self, func_list: List[Callable], interrupt_on_failure=False):
        all_pass = True
        for task in self.undone_tasks:
            task_pass = True
            for func in func_list:
                if not func(task):
                    if interrupt_on_failure:
                        return False
                    task_pass = False
                    all_pass = False
            else:
                if task_pass:
                    task.set_done()
        return all_pass


class ChildWorkflowHandler:

    @property
    def child_flows_ids(self: Workflow):
        if 'child_flow_ids' not in self.arguments:
            self.update_arguments({'child_flow_ids': []})
        return self.arguments.get('child_flow_ids')

    @child_flows_ids.setter
    def child_flows_ids(self: Workflow, id_list: list):
        self.update_arguments({'child_flow_ids': id_list})

    @property
    def child_flows(self) -> Iterable[Flow]:
        for flow_id in self.child_flows_ids:
            yield Flow.objects.get(id=flow_id)

    def append_child_flow(self, flow: Flow):
        flows_ids = self.child_flows_ids
        flows_ids.append(flow.id)
        self.child_flows_ids = flows_ids

    def check_child_flows_done(self):
        for flow in self.child_flows:
            if flow.processing_state != FlowState.DONE:
                return False
        else:
            return True

    def distribute_children_on_timeline(self, start_delay: int, step: int):
        delay = start_delay
        for flow in self.child_flows:
            logger.debug(f'Postpone child flow for {delay}')
            flow.postponed = now() + timedelta(seconds=delay)
            flow.save()
            delay += step
