from django.urls import path

from ticker import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:ticker_id>/', views.ticker_base, name='ticker_summary'),
    path('<int:ticker>/daily', views.ticker_daily, name='ticker_daily'),
    path('<int:ticker>/finviz_fundamental', views.finviz_fundamental, name='finviz_fundamental'),
]
