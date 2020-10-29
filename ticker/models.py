from django.db import models


class AbstractStock(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    ticker = models.CharField(max_length=6)

    class Meta:
        abstract = True

    def __str__(self):
        return self.ticker


class Etf(AbstractStock):
    pass


class Stock(AbstractStock):
    company = models.CharField(max_length=100)
    etf = models.ManyToManyField(Etf)
