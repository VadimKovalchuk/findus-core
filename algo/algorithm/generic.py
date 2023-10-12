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

    def convert_for_db(self):
        return {
            'name': self.name,
            'weight': self.weight,
            'normalization_method': self.normalization_method
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
        self.algo = Algo.model.create(name=self.name, reference_scope=self.scope)
        for metric in self.metrics:
            db_metric: AlgoMetric = AlgoMetric.model.create(**metric.convert_for_db())
            db_metric.save()

    def _convert_metric_for_db(self, metric: Metric):
        result: Dict = metric.convert_for_db()
        result.update({
            'algo': self.algo
        })

    def validate_db_correspondence(self):
        db_entries = Algo.model.get(name=self.name)
        if db_entries.count() > 1:
            raise ReferenceError(f'More than one Algo instance detected for {self.name} algorithm')
        if not db_entries.count():
            self.deploy()
        algo: Algo = db_entries[0]

    def calculate_parameters(self):
        pass

    def perform_slice(self):
        pass

