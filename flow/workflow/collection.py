from datetime import timedelta


from django.utils.timezone import now

from flow.workflow.generic import Workflow
from task.models import NetworkTask, TaskState
from task.lib.processing import append_new_tickers, update_scope


class ScopeUpdateWorklow(Workflow):
    flow_name = 'update_ticker_list'

    def stage_0(self):
        task_ids = []
        for scope_name in ["SP500", "SP400", "SP600"]:
            task = NetworkTask.objects.create(
                name=f'update_{scope_name.lower()}_ticker_list',
                flow=self.flow,
                module='findus_edge.tickers',
                function='get_scope',
            )
            task.arguments_dict = {"scope": scope_name}
            task.save()
            task_ids.append(task.id)
        self.flow.arguments_dict = {'task_ids': task_ids}
        self.flow.save()
        return True

    def stage_1(self):
        task_ids = self.flow.arguments_dict['task_ids']
        for task_id in task_ids:
            task = NetworkTask.objects.get(id=task_id)
            if task.state != TaskState.PROCESSED:
                return False
        else:
            return True

    def stage_2(self):
        task_ids = self.flow.arguments_dict['task_ids']
        all_pass = True
        for task_id in task_ids:
            task = NetworkTask.objects.get(id=task_id)
            if task.state == TaskState.PROCESSED:
                if append_new_tickers(task) and update_scope(task):
                    task.state = TaskState.DONE
                    task.postponed = now() + timedelta(days=92)
                    task.save()
                else:
                    all_pass = False
        return all_pass
