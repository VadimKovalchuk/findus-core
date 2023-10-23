from dataclasses import dataclass
from typing import Dict, List, Type, Union

from django.db.models import Model

from algo.models import Algo, AlgoMetric
from ticker.models import Scope


@dataclass
class Metric:
    name: str
    weight: float
    normalization_method: str
    target_model: Type[Model]
    target_field: str
    min_threshold: Union[float, None]
    max_threshold: Union[float, None]

    def convert_for_db(self):
        return {
            'name': self.name,
            'weight': self.weight,
            'normalization_method': self.normalization_method,
            'min_threshold': self.min_threshold,
            'max_threshold': self.max_threshold
        }


class Algorithm:
    name: str = 'generic'
    metrics: List[Metric] = []
    scope: Union[Scope, None] = None

    def __init__(self, algo: Algo = None):
        self.algo = algo

    def save(self):
        self.algo.save()

    def deploy(self):
        self.algo = Algo.objects.create(name=self.name, reference_scope=self.scope)
        for metric in self.metrics:
            algo_metric_args = self._convert_metric_for_db(metric)
            db_metric: AlgoMetric = AlgoMetric.objects.create(**algo_metric_args)
            db_metric.save()

    def _convert_metric_for_db(self, metric: Metric):
        result: Dict = metric.convert_for_db()
        result.update({
            'algo': self.algo
        })
        return result

    def get_metric_by_name(self, name: str, from_db: bool = False):
        # TODO: Convert metric from DB if from_db is true
        for metric in self.metrics:
            if name == metric.name:
                return metric
        else:
            raise AttributeError(f'Referencing missing metric "{name}" in algorithm "{self.name}"')

    def validate_db_correspondence(self):
        db_entries = Algo.objects.filter(name=self.name)
        if db_entries.count() > 1:
            raise ReferenceError(f'More than one Algo instance detected for {self.name} algorithm')
        if not db_entries.count():
            self.deploy()
        algo: Algo = db_entries[0]
        algo_metric_names = [algo_metric.name for algo_metric in algo.metrics]
        for metric in self.metrics:
            if metric.name not in algo_metric_names:
                raise AttributeError(f'Metric {metric.name} is missing in algo metric list')
        for metric_name in algo_metric_names:
            if metric_name not in [metric.name for metric in self.metrics]:
                raise AttributeError(f'Redundant metric {metric_name} is found in algo metric list')

    def collect_metric_normalization_data(self, metric: Metric):
        data = {}
        tickers = self.algo.reference_scope.tickers.all()
        for tkr in tickers:
            # TODO: Refactor query filter
            _obj = metric.target_model.objects.filter(ticker=tkr).last()
            if not _obj:  # Ignore ticker if it has no reference model instances
                continue
            value = getattr(_obj, metric.target_field, None)
            if value is None:  # Ignore empty field of corresponding reference model
                continue
            if metric.max_threshold and metric.max_threshold < value:  # Ignore value if it is over max limit
                continue
            if metric.min_threshold and metric.min_threshold > value:  # Ignore value if it is under min limit
                continue
            data[_obj.id] = value
        return data

    def store_parameters(self):
        pass

    def get_slice_source_data(self):
        pass

    def create_slice_after_processing(self):
        pass

