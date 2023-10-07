from django.urls import path

from ticker import views

urlpatterns = [
    path('', views.TickerListView.as_view(), name='ticker_list'),
    path('<int:ticker_pk>/', views.ticker_base, name='ticker_summary'),
    path('<int:ticker_pk>/daily', views.ticker_daily, name='ticker_daily'),
    path('<int:ticker_pk>/finviz_fundamental', views.finviz_fundamental, name='finviz_fundamental'),
]
