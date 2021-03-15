from django.db import models


class AbstractTicker(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    symbol = models.CharField(max_length=6)

    class Meta:
        abstract = True

    def __str__(self):
        return self.symbol


class Ticker(AbstractTicker):
    company = models.CharField(max_length=100)


class Price(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    date = models.DateTimeField()
    open = models.FloatField(null=True)
    high = models.FloatField(null=True)
    low = models.FloatField(null=True)
    close = models.FloatField(null=True)
    volume = models.FloatField(null=True)


class Dividend(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    date = models.DateTimeField()
    size = models.FloatField()
