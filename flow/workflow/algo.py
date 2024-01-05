import json
import logging
from datetime import timedelta
from typing import Dict, List

from django.utils.timezone import now

from algo.models import Algo, AlgoMetric, AlgoSlice, AlgoMetricSlice
from algo.processing import collect_normalization_data, append_slices
from flow.models import Flow
from flow.workflow.generic import Workflow, TaskHandler
from task.models import Task, TaskState
from ticker.models import Ticker


class CalculateAlgoMetricsWorkflow(Workflow, TaskHandler):
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
        return True

    def stage_1(self):
        return self.check_all_task_processed()

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

        for task in self.tasks:
            if set_metric_params(task) and append_slices(task):
                task.set_done()
            else:
                return False
        else:
            return True


class ApplyAlgoMetricsWorkflow(Workflow, TaskHandler):
    flow_name = 'apply_algo_metrics'
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
        ticker = Ticker.objects.get(symbol=self.arguments['ticker'])
        for metric in algo.metrics:
            metric_argument = metric.get_ticker_data(ticker)
            if metric_argument is None:
                continue
            task = Task.objects.create(
                name='apply_metric',
                flow=self.flow,
                module='findus_edge.algo.normalization',
                function='normalization',
            )
            task.arguments_dict = {
                "input_data": metric_argument,
                "norm_method": metric.normalization_method,
                "metric_id": metric.id,
                "parameters": metric.method_parameters_dict,
            }
            task.save()
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):
        for task in self.tasks:
            if append_slices(task):
                task.set_done()
            else:
                return False
        else:
            return True


class WeightMetricsWorkflow(Workflow, TaskHandler):
    flow_name = 'weight_algo_metrics'
    '''
    Flow arguments dict should have following keys:
     - algo_name
     - is_reference - whether reference metric values should be used
    '''
    def stage_0(self):
        for key in ['algo_name', 'is_reference', 'ticker']:
            if key not in self.arguments:
                raise ValueError(f'{key} is not defined for algorythm metrics based rate workflow')
        algo = Algo.objects.get(name=self.arguments['algo_name'])
        task_arguments = {}
        ticker = Ticker.objects.get(symbol=self.arguments['ticker'])
        algo_slices: AlgoSlice = AlgoSlice.objects.filter(algo=algo, ticker=ticker)
        algo_slice: AlgoSlice = algo_slices.last()
        for metric_slice in algo_slice.metrics:
            metric = metric_slice.metric
            task_arguments[metric.name] = {'value': metric_slice.result, 'weight': metric.weight}
        task = Task.objects.create(
            name='weight_metrics',
            flow=self.flow,
            module='findus_edge.algo.metrics',
            function='weight',
        )
        # print(json.dumps(task_arguments,indent=4))
        task.arguments_dict = task_arguments
        task.save()
        self.arguments_update({'algo_slice_id': algo_slice.id})
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):
        def set_rate_value(task: Task):
            algo_slice: AlgoSlice = AlgoSlice.objects.get(id=algo_slice_id)
            algo_slice.result = task.result
            algo_slice.save()
            return True

        algo_slice_id = self.arguments['algo_slice_id']
        for task in self.tasks:
            if set_rate_value(task):
                task.state = TaskState.DONE
                task.postponed = now() + timedelta(days=92)
                task.save()
            else:
                return False
        else:
            return True
