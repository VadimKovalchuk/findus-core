import sys
import inspect

from algo.models import Algo
from task.models import Task


def get_metrics(task: Task):
    args = task.arguments_dict
    algo_name = args['algo_id']
    algo = Algo.objects.get(name=algo_name)
    args['metric_ids'] = [metric.id for metric in algo.metrics]
    task.arguments_dict = args
    return True


ALGO_PROCESSING_FUNCTIONS = {name: obj for name, obj in inspect.getmembers(sys.modules[__name__])}
