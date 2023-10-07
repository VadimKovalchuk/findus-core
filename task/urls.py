from django.urls import path

from ticker import views

urlpatterns = [
    path('', views.index, name='index'),
]