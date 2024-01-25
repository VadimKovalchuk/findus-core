import json
import logging
from datetime import timedelta
from typing import Dict, List

from django.utils.timezone import now

from algo.models import Algo, AlgoMetric, AlgoSlice, AlgoMetricSlice
from algo.processing import collect_normalization_data, append_slices
from flow.models import Flow
from flow.workflow.generic import Workflow, TaskHandler, ChildWorkflowHandler
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

        return self.map_task_results([set_metric_params, append_slices])


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
        return self.map_task_results([append_slices])


class RateAlgoSliceWorkflow(Workflow, TaskHandler):
    flow_name = 'weight_algo_slice'
    '''
    Flow arguments dict should have following keys:
     - algo_name
     - is_reference - whether reference metric values should be used
    '''
    def stage_0(self):
        if 'algo_slice_id' not in self.arguments:
            raise ValueError('algo_slice_id is not defined for algorythm metrics based rate workflow')
        algo_slice: AlgoSlice = AlgoSlice.objects.get(id=self.arguments['algo_slice_id'])
        task_arguments = {"algo_slice_id": self.arguments['algo_slice_id'], "metrics": {}}
        for metric_slice in algo_slice.metrics:
            metric = metric_slice.metric
            task_arguments['metrics'][metric.name] = {'value': metric_slice.result, 'weight': metric.weight}
        task = Task.objects.create(
            name='weight_metrics',
            flow=self.flow,
            module='findus_edge.algo.metrics',
            function='weight',
        )
        task.arguments_dict = task_arguments
        task.save()
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):
        def set_rate_value(task: Task):
            algo_slice_id = task.arguments_dict['algo_slice_id']
            algo_slice: AlgoSlice = AlgoSlice.objects.get(id=algo_slice_id)
            algo_slice.result = task.result_dict['rate']
            algo_slice.save()
            return True

        return self.map_task_results([set_rate_value])


class RateAllSlicesWorkflow(Workflow, ChildWorkflowHandler):
    flow_name = 'rate_all_algo_slices'
    '''
    Flow arguments dict should have following keys:
     - algo_name
     - is_reference - whether reference metric values should be used
    '''
    def stage_0(self):
        if 'algo_name' not in self.arguments:
            raise ValueError('"algo_name" is not defined for algorythm metrics based rate workflow')
        algo = Algo.objects.get(name=self.arguments['algo_name'])
        algo_slices: List[AlgoSlice] = AlgoSlice.objects.filter(algo=algo, result__isnull=True)
        for algo_slice in algo_slices:
            workflow = RateAlgoSliceWorkflow()
            flow = workflow.create()
            workflow.arguments = {'algo_slice_id': algo_slice.id}
            self.append_child_flow(flow)
        return True

    def stage_1(self):
        return self.check_child_flows_done()
