from flow.workflow.generic import Workflow, TaskHandler
from task.models import Task, TaskState
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
        task = Task.objects.create(
            name='network_relay_task',
            flow=self.flow,
            module='builtin',
            function='relay',
        )
        task.arguments_dict = {'foo': 'bar'}
        task.save()
        return True

    def stage_1(self):
        task = Task.objects.get(name='network_relay_task')
        print(task.state)
        return False


class TestScopeWorklow(Workflow, TaskHandler):
    flow_name = 'test_scope'

    def stage_0(self):
        task = Task.objects.create(
            name='update_test_scope',
            flow=self.flow,
            module='findus_edge.tickers',
            function='update_test_scope',
        )
        task.arguments_dict = {"scope": "TestScope"}
        task.save()
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):
        task = self.tasks[0]
        return append_new_tickers(task) and update_scope(task)
