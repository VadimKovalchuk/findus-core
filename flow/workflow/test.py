from flow.models import Flow
from flow.workflow.generic import Workflow
from task.models import NetworkTask


class TestStagesWorklow(Workflow):
    flow_name = 'test_stages'

    def stage_0(self):
        return True

    def stage_1(self):
        return True

    def stage_2(self):
        return True

    def stage_3(self):
        return True

    def stage_4(self):
        return True


class TestRelayWorklow(Workflow):
    flow_name = 'test_relay'

    def stage_0(self):
        task = NetworkTask.objects.create(
            name='network_relay_task',
            flow=self.flow,
            module='builtin',
            function='relay',
        )
        task.arguments_dict = {'foo': 'bar'}
        task.save()
        return True

    def stage_1(self):
        task = NetworkTask.objects.get(name='network_relay_task')
        print(task.state)
        return False
