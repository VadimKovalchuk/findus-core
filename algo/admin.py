from django.contrib import admin

from .models import Algo, AlgoMetric, AlgoSlice, AlgoMetricSlice

admin.site.register(Algo)
admin.site.register(AlgoMetric)
admin.site.register(AlgoSlice)
admin.site.register(AlgoMetricSlice)
