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
    reference_scope: Scope = models.ForeignKey(Scope, null=True, on_delete=models.SET_NULL)

    @property
    def metrics(self):
        return self.algometric_set.all()

    def get_slices_by_ticker(self, ticker: Ticker):
        assert ticker in self.reference_scope.tickers.all(), \
            f'Ticker {ticker} is missing in {self.reference_scope} scope'
        return self.algoslice_set.filter(ticker=ticker)

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
    min_threshold = models.FloatField(null=True, help_text='minimal metric value that can be used in calculations')
    max_threshold = models.FloatField(null=True, help_text='maximum metric value that can be used in calculations')
    method_parameters = models.TextField(default='{}', help_text='Normalization method parameters')

    @property
    def method_parameters_dict(self):
        return json.loads(self.method_parameters)

    @method_parameters_dict.setter
    def method_parameters_dict(self, _dict: dict):
        self.method_parameters = json.dumps(_dict)

    @property
    def target_model_class(self):
        return METRIC_MODELS_REFERENCE.get(self.target_model)

    def get_normalization_data(self):
        data = {}
        tickers = self.algo.reference_scope.tickers.all()
        for tkr in tickers:
            # TODO: Refactor query filter
            _obj = self.target_model_class.objects.filter(ticker=tkr).last()
            if not _obj:  # Ignore ticker if it has no reference model instances
                continue
            value = getattr(_obj, self.target_field, None)
            if value is None:  # Ignore empty field of corresponding reference model
                continue
            if self.max_threshold and self.max_threshold < value:  # Ignore value if it is over max limit
                continue
            if self.min_threshold and self.min_threshold > value:  # Ignore value if it is under min limit
                continue
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
    slice = models.ForeignKey(AlgoSlice, on_delete=models.CASCADE)
    metric = models.ForeignKey(AlgoMetric, on_delete=models.CASCADE)
    result = models.FloatField(null=True, help_text='metric rating')

    def __str__(self):
        return f'({self.id})"{self.metric.algo.name}/{self.metric.name}":{self.result}'
