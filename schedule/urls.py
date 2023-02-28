from django.urls import path

from schedule import views

urlpatterns = [
    path('', views.EventListView.as_view(), name='scheduled_events'),
    path('<int:schedule_id>', views.schedule_details, name='schedule_details'),
    path('event/<int:event_id>', views.event, name='event_details')
]
