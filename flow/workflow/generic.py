from flow.models import Flow

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

    def get_active_stage_method(self):
        if not self.flow:
            raise AttributeError('Flow attribute is not set')
        if self.flow.stage > self.stage_count:
            raise AttributeError('Flow active stage is more than total stage count')
        return getattr(self, f'stage_{self.flow.stage}')

    def create(self):
        self.flow = Flow.objects.create(name=self.flow_name)
        return self.flow

    def stage_0(self):
        return True
