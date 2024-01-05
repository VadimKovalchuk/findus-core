from typing import Dict, List

from django.db.models import Q

from flow.models import Flow
from task.models import Task, TaskState

STAGE_COUNT_CAP = 100


class Workflow:
    flow_name = 'generic'

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
        self.validate_flow()
        return self.flow.stage

    @stage.setter
    def stage(self, stage: str):
        self.validate_flow()
        self.flow.stage = stage
        self.flow.save()

    @property
    def arguments(self):
        self.validate_flow()
        return self.flow.arguments_dict

    @arguments.setter
    def arguments(self, _dict: Dict):
        self.flow.arguments_dict = _dict
        self.flow.save()

    def validate_flow(self):
        if not self.flow:
            raise AttributeError('Flow attribute is not set')

    def save(self):
        self.validate_flow()
        self.flow.save()

    def arguments_update(self, _dict: Dict):
        arguments: Dict = self.arguments
        arguments.update(_dict)
        self.arguments = arguments

    def check_last_stage(self):
        self.validate_flow()
        return self.stage_count == self.stage + 1

    def get_active_stage_method(self):
        self.validate_flow()
        if self.flow.stage > self.stage_count:
            raise AttributeError('Flow active stage is more than total stage count')
        return getattr(self, f'stage_{self.flow.stage}')

    def create(self):
        self.flow = Flow.objects.create(name=self.flow_name)
        return self.flow

    def stage_0(self):
        return True


class TaskHandler:

    @property
    def tasks(self) -> List[Task]:
        return self.flow.task_set.all()

    @property
    def undone_tasks(self) -> List[Task]:
        return self.flow.task_set.filter(~Q(processing_state=TaskState.DONE))

    def check_all_task_processed(self):
        processed = self.flow.task_set.filter(processing_state=TaskState.PROCESSED)
        print((len(processed), len(self.undone_tasks)))
        print(len(processed) == len(self.undone_tasks))
        return len(processed) == len(self.undone_tasks)


class ChildWorkflowHandler:
    pass
