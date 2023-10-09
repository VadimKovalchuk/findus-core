from dataclasses import dataclass

from django.db.models import Model

from algo.models import Algo


@dataclass
class Metric:
    name: str
    weight: float
    normalization_method: str
    target_model: Model
    target_field: str


class Algorithm:
    name = 'generic'
    metrics = {}

    def __init__(self, algo: Algo = None):
        self.algo = algo

    def save(self):
        self.algo.save()

    def deploy(self):
        pass

    def _convert_metric_for_db(self, metric: Metric):
        pass

    def validate_db_correspondence(self):
        db_entries = Algo.model.get(name=self.name)
        if db_entries.count() > 1:
            raise ReferenceError(f'More than one Algo instance detected for {self.name} algorithm')
        if not db_entries.count():
            self.deploy()
        algo: Algo = db_entries[0]

