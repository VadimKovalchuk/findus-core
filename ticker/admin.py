from django.contrib import admin

from ticker.models import Ticker, Price, Dividend, FinvizFundamental

admin.site.register(Ticker)
admin.site.register(Price)
admin.site.register(Dividend)
admin.site.register(FinvizFundamental)
