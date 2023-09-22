from datetime import timedelta
from typing import Dict, List

from django.utils.timezone import now

from algo.models import Algo
from algo.processing import collect_normalization_data, set_metric_params, append_slices, get_metrics
from flow.models import Flow
from flow.workflow.generic import Workflow
from task.models import NetworkTask, TaskState


class CalculateAlgoMetricWorkflow(Workflow):
    flow_name = 'calculate_metric'

    def stage_0(self):
        if 'metric_ids' not in self.arguments:
            raise ValueError('Metric ID is not defined for algorythm metric calculation workflow')
        task = NetworkTask.objects.create(
            name='calculate_metric',
            flow=self.flow,
            module='findus_edge.algo.normalization',
            function='normalization',
        )
        collect_normalization_data(task)
        self.arguments_update({'task_id': task.id})
        return True

    def stage_1(self):
        task_id = self.arguments['task_id']
        task = NetworkTask.objects.get(id=task_id)
        return task.state == TaskState.PROCESSED

    def stage_2(self):
        task_id = self.arguments['task_id']
        task = NetworkTask.objects.get(id=task_id)
        done = set_metric_params(task) and append_slices(task)
        if done:
            task.state = TaskState.DONE
            task.postponed = now() + timedelta(days=92)
            task.save()
        return done


class CalculateAllAlgoMetricsWorkflow(Workflow):
    flow_name = 'calculate_algo_metrics'

    def stage_0(self):
        if 'algo_id' not in self.arguments:
            raise ValueError('Algo ID is not defined for algorythm metric calculation workflow')
        child_flow_ids: List = []
        algo = Algo.objects.get(id=self.arguments['algo_id'])
        for metric_id in [metric.id for metric in algo.metrics]:
            workflow = CalculateAlgoMetricWorkflow()
            flow = workflow.create()
            workflow.arguments = {'metric_ids': metric_id}
            child_flow_ids.append(flow.id)
            self.arguments_update({'child_flow_ids': child_flow_ids})
        self.flow.refresh_from_db()
        # print(self.arguments)
        return True

    def stage_1(self):
        child_flow_ids: List = self.arguments['child_flow_ids']
        for flow_id in child_flow_ids:
            flow = Flow.objects.get(id=flow_id)
            if flow.processing_state != TaskState.DONE:
                return False
        else:
            return True

