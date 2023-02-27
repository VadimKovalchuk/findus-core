from django.urls import path

from schedule import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:schedule_id>', views.schedule_details, name='schedule_details'),
    path('event/<int:event_id>', views.event, name='event')
]
