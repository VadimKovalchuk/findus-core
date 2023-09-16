from flow.workflow.generic import Workflow
from task.models import NetworkTask, TaskState
from task.lib.processing import append_new_tickers, update_scope


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


class TestScopeWorklow(Workflow):
    flow_name = 'test_scope'

    def stage_0(self):
        task = NetworkTask.objects.create(
            name='update_test_scope',
            flow=self.flow,
            module='findus_edge.tickers',
            function='update_test_scope',
        )
        task.arguments_dict = {"scope": "TestScope"}
        task.save()
        self.flow.arguments_dict = {'task_id': task.id}
        self.flow.save()
        return True

    def stage_1(self):
        task_id = self.flow.arguments_dict['task_id']
        task = NetworkTask.objects.get(id=task_id)
        return task.state == TaskState.PROCESSED

    def stage_2(self):
        task_id = self.flow.arguments_dict['task_id']
        task = NetworkTask.objects.get(id=task_id)
        return append_new_tickers(task) and update_scope(task)
