from django.db import models

from ticker.models import Ticker, Scope


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
