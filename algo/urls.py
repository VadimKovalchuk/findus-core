from django.urls import path

from algo import views

urlpatterns = [
    path('', views.AlgoListView.as_view(), name='algo_index'),
    path('<int:algo_pk>', views.algo_details, name='algo_details'),
]
