from dataclasses import dataclass
from typing import Dict, List, Type, Union

from algo.models import Algo, AlgoMetric
from ticker.models import Scope


@dataclass
class Metric:
    name: str
    weight: float
    normalization_method: str
    target_model: str
    target_field: str
    algo: Union[None, Algo] = None
    min_threshold: Union[float, None] = None
    max_threshold: Union[float, None] = None


class Algorithm:
    name: str = 'generic'
    default_metrics: List[Metric] = []
    scope: Union[Scope, None] = None

    def __init__(self, algo: Algo = None):
        self.algo = algo

    def save(self):
        self.algo.save()

    def deploy(self):
        self.algo = Algo.objects.create(name=self.name, reference_scope=self.scope)
        for metric in self.default_metrics:
            metric.algo = self.algo
            db_metric: AlgoMetric = AlgoMetric.objects.create(**(metric.__dict__))
            db_metric.save()

    def validate_db_correspondence(self):
        db_entries = Algo.objects.filter(name=self.name)
        if db_entries.count() > 1:
            raise ReferenceError(f'More than one Algo instance detected for {self.name} algorithm')
        if not db_entries.count():
            self.deploy()
        algo: Algo = db_entries[0]
        algo_metric_names = [algo_metric.name for algo_metric in algo.metrics]
        for metric in self.default_metrics:
            if metric.name not in algo_metric_names:
                raise AttributeError(f'Metric {metric.name} is missing in algo metric list')
        for metric_name in algo_metric_names:
            if metric_name not in [metric.name for metric in self.default_metrics]:
                raise AttributeError(f'Redundant metric {metric_name} is found in algo metric list')

    def collect_metric_normalization_data(self, metric: Metric):
        pass

    def store_parameters(self):
        pass

    def get_slice_source_data(self):
        pass

    def create_slice_after_processing(self):
        pass

