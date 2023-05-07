import logging
import sys
import inspect

from algo.models import Algo, AlgoMetric
from task.models import Task


logger = logging.getLogger(__name__)


def get_metrics(task: Task):
    args = task.arguments_dict
    algo_id = args['algo_id']
    algo = Algo.objects.get(id=algo_id)
    args['metric_ids'] = [metric.id for metric in algo.metrics]
    task.arguments_dict = args
    task.save()
    return True


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
    logger.debug(result)
    calculated_parameters = result['parameters']
    logger.debug(calculated_parameters)
    metric_params = metric.method_parameters_dict
    logger.debug(metric_params)
    metric_params.update(calculated_parameters)
    logger.debug(metric_params)
    metric.method_parameters_dict = metric_params
    metric.save()
    return True


ALGO_PROCESSING_FUNCTIONS = {name: obj for name, obj in inspect.getmembers(sys.modules[__name__])}
