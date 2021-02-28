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
