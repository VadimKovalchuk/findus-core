import json

from django.db import models

from ticker.models import Ticker, Scope


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
    normalization_method = models.CharField(max_length=20)
    method_parameters = models.TextField(default='{}', help_text='Normalization method parameters')

    @property
    def method_parameters_dict(self):
        return json.loads(self.method_parameters)

    @method_parameters_dict.setter
    def method_parameters_dict(self, _dict: dict):
        self.method_parameters = json.dumps(_dict)

    @property
    def limits(self):
        return self.method_parameters_dict.get('limits', {})

    def get_normalization_data(self, ignore_empty=True):
        data = {}
        tickers = self.algo.reference_scope.tickers.all()
        limits = self.limits
        for tkr in tickers:
            _obj = self.target_model_class.objects.filter(ticker=tkr).last()
            # Ignore ticker if it has no reference model instances
            if not _obj:
                continue
            value = _obj.__dict__.get(self.target_field)
            # Ignore empty field of corresponding reference model
            if value is None and ignore_empty:
                continue
            # In case if metric field has reference data limits
            if limits:
                # Ignore value if it is over max limit
                _max = limits.get("max")
                if _max and _max < value:
                    continue
                # Ignore value if it is under min limit
                _min = limits.get("min")
                if _min and _min > value:
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
