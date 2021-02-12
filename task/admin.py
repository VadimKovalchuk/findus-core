from django.contrib import admin

from .models import SystemTask, NetworkTask

admin.site.register(SystemTask)
admin.site.register(NetworkTask)
