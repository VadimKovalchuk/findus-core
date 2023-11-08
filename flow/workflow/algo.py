from datetime import timedelta
from typing import Dict, List

from django.utils.timezone import now

from algo.models import Algo, AlgoMetric
from algo.processing import collect_normalization_data, append_slices
from flow.models import Flow
from flow.workflow.generic import Workflow
from task.models import Task, TaskState


class CalculateAlgoMetricsWorkflow(Workflow):
    flow_name = 'calculate_algo_metrics'
    '''
    Flow arguments dict should have following keys:
     - algo_name
     - is_reference - whether reference metric values should be used
    '''
    def stage_0(self):
        for key in ['algo_name', 'is_reference']:
            if key not in self.arguments:
                raise ValueError(f'{key} is not defined for algorythm metric calculation workflow')
        algo = Algo.objects.get(name=self.arguments['algo_name'])
        task_ids = []
        for metric in algo.metrics:
            task = Task.objects.create(
                name='calculate_metric',
                flow=self.flow,
                module='findus_edge.algo.normalization',
                function='normalization',
            )
            task.arguments_dict = {
                "input_data": metric.get_normalization_data(),
                "norm_method": metric.normalization_method,
                "metric_id": metric.id
                # "parameters": metric.method_parameters_dict
            }
            task.save()
            task_ids.append(task.id)
        self.arguments_update({'task_ids': task_ids})
        return True

    def stage_1(self):
        task_ids = self.arguments['task_ids']
        for task_id in task_ids:
            task = Task.objects.get(id=task_id)
            if task.state != TaskState.PROCESSED:
                return False
        else:
            return True

    def stage_2(self):
        def set_metric_params(task: Task):
            args = task.arguments_dict
            metric_id = args['metric_id']
            metric: AlgoMetric = AlgoMetric.objects.get(id=metric_id)
            result = task.result_dict
            calculated_parameters = result['parameters']
            metric_params = metric.method_parameters_dict
            metric_params.update(calculated_parameters)
            metric.method_parameters_dict = metric_params
            metric.save()
            return True

        task_ids = self.arguments['task_ids']
        for task_id in task_ids:
            task = Task.objects.get(id=task_id)
            done = set_metric_params(task)  and append_slices(task)
            if done:
                task.state = TaskState.DONE
                task.postponed = now() + timedelta(days=92)
                task.save()
        return done


class ApplyAlgoNormalizationWorkflow(Workflow):
    flow_name = 'apply_algo_normalization'
    '''
    Flow arguments dict should have following keys:
     - algo_name
     - is_reference - whether reference metric values should be used
    '''
    def stage_0(self):
        for key in ['algo_name', 'ticker']:
            if key not in self.arguments:
                raise ValueError(f'{key} is not defined for algorythm metric calculation workflow')
        algo = Algo.objects.get(name=self.arguments['algo_name'])
        task_ids = []
        for metric in algo.metrics:
            task = Task.objects.create(
                name='calculate_metric',
                flow=self.flow,
                module='findus_edge.algo.normalization',
                function='normalization',
            )
            task.arguments_dict = {
                "input_data": metric.get_normalization_data(),
                "norm_method": metric.normalization_method,
                "metric_id": metric.id
                # "parameters": metric.method_parameters_dict
            }
            task.save()
            task_ids.append(task.id)
        self.arguments_update({'task_ids': task_ids})
        return True

    def stage_1(self):
        task_ids = self.arguments['task_ids']
        for task_id in task_ids:
            task = Task.objects.get(id=task_id)
            if task.state != TaskState.PROCESSED:
                return False
        else:
            return True

    def stage_2(self):
        def set_metric_params(task: Task):
            args = task.arguments_dict
            metric_id = args['metric_id']
            metric: AlgoMetric = AlgoMetric.objects.get(id=metric_id)
            result = task.result_dict
            calculated_parameters = result['parameters']
            metric_params = metric.method_parameters_dict
            metric_params.update(calculated_parameters)
            metric.method_parameters_dict = metric_params
            metric.save()
            return True

        task_ids = self.arguments['task_ids']
        for task_id in task_ids:
            task = Task.objects.get(id=task_id)
            done = set_metric_params(task)  and append_slices(task)
            if done:
                task.state = TaskState.DONE
                task.postponed = now() + timedelta(days=92)
                task.save()
        return done
