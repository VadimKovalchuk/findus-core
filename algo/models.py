import json

from django.db import models

from ticker.models import Ticker, Scope, FinvizFundamental, Price, Dividend


METRIC_MODELS_REFERENCE = {
    'Dividend': Dividend,
    'FinvizFundamental': FinvizFundamental,
    'Price': Price
}


class Algo(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    name = models.TextField()
    reference_scope = models.ForeignKey(Scope, null=True, on_delete=models.SET_NULL)

    @property
    def metrics(self):
        return self.algometric_set.all()

    def __str__(self):
        return f'({self.id}) "{self.name}"'  # : {self.scope}'


class AlgoMetric(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    name = models.TextField()
    algo = models.ForeignKey(Algo, on_delete=models.CASCADE)
    weight = models.FloatField(help_text='metric weight in final rating')
    target_model = models.CharField(max_length=100, help_text='calculated Django model')
    target_field = models.CharField(max_length=100, help_text='Django model calculated field')
    normalization_method = models.CharField(max_length=20)
    method_parameters = models.TextField(help_text='Normalization method parameters')

    @property
    def method_parameters_dict(self):
        return json.loads(self.method_parameters)

    @method_parameters_dict.setter
    def method_parameters_dict(self, _dict: dict):
        self.method_parameters = json.dumps(_dict)

    @property
    def limits(self):
        return self.method_parameters_dict.get('limits', {})

    @property
    def target_model_class(self):
        return METRIC_MODELS_REFERENCE.get(self.target_model)

    def get_normalization_data(self, ignore_empty=True):
        data = {}
        tickers = self.algo.reference_scope.tickers.all()
        for tkr in tickers:
            _obj = self.target_model_class.objects.filter(ticker=tkr).last()
            if not _obj:
                continue
            value = _obj.__dict__.get(self.target_field)
            if value or not ignore_empty:
                data[_obj.id] = value
        return data

    def __str__(self):
        return f'({self.id}) "{self.name}" of {self.algo.name}'


class AlgoSlice(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    algo = models.ForeignKey(Algo, on_delete=models.CASCADE)
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    date = models.DateTimeField()
    result = models.FloatField(null=True, help_text='final rating')

    @property
    def metrics(self):
        return self.algometricslice_set.all()

    def __str__(self):
        return f' ({self.id})"{self.algo.name}" for {self.ticker.symbol}:{self.result} at {self.date}'


class AlgoMetricSlice(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    metric = models.ForeignKey(AlgoMetric, on_delete=models.CASCADE)
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    result = models.FloatField(null=True, help_text='metric rating')

    def __str__(self):
        return f'({self.id})"{self.metric.algo.name}/{self.metric.name}":{self.result}'
