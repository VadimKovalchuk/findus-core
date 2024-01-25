import logging
import sys
import inspect

from django.utils.timezone import now

from algo.models import Algo, AlgoMetric, AlgoSlice, AlgoMetricSlice
from task.models import Task


logger = logging.getLogger(__name__)


def collect_normalization_data(task: Task):
    args = task.arguments_dict
    metric_id = args['metric_ids']
    metric: AlgoMetric = AlgoMetric.objects.get(id=metric_id)
    args.update(
        {
            "input_data": metric.get_normalization_data(),
            "norm_method": metric.normalization_method,
            "parameters": metric.method_parameters_dict
        }
    )
    # logger.debug(args)
    task.arguments_dict = args
    task.save()
    return True


def set_metric_params(task: Task):
    args = task.arguments_dict
    metric_id = args['metric_ids']
    metric: AlgoMetric = AlgoMetric.objects.get(id=metric_id)
    result = task.result_dict
    calculated_parameters = result['parameters']
    metric_params = metric.method_parameters_dict
    metric_params.update(calculated_parameters)
    metric.method_parameters_dict = metric_params
    metric.save()
    return True


def append_slices(task: Task):
    args = task.arguments_dict
    metric_id = args['metric_id']
    metric: AlgoMetric = AlgoMetric.objects.get(id=metric_id)
    result = task.result_dict
    normalized = result['result']
    for model_obj_id in normalized:
        model_obj = metric.target_model_class.objects.get(id=model_obj_id)
        algo_slices: AlgoSlice = AlgoSlice.objects.filter(algo=metric.algo, ticker=model_obj.ticker, date=now().date())
        if algo_slices:
            algo_slice: AlgoSlice = algo_slices.last()
        else:
            algo_slice: AlgoSlice = AlgoSlice.objects.create(algo=metric.algo, ticker=model_obj.ticker, date=now().date())
            algo_slice.save()
        # logger.debug(algo_slice)
        metric_slice: AlgoMetricSlice = AlgoMetricSlice.objects.create(slice=algo_slice, metric=metric, result=normalized[model_obj_id])
        metric_slice.save()
        # logger.debug(metric_slice)
    return True


ALGO_PROCESSING_FUNCTIONS = {name: obj for name, obj in inspect.getmembers(sys.modules[__name__])}
