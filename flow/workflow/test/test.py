from flow.models import Flow
from task.models import NetworkTask


class TestRelayFlow:

    def stage_1(self):
        task = NetworkTask.objects.create(
            name='network_relay_task',
            module='builtin',
            function='relay',
        )
        task.arguments_dict = {'foo': 'bar'}
        task.save()
        return True

    def stage_2(self):
        task = NetworkTask.objects.get(name='network_relay_task')
        print(task.state)
        return False
