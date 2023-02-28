from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic.list import ListView

from schedule.models import Event


def index(request):
    return HttpResponse("Schedule!")


class EventListView(ListView):
    model = Event


def schedule_details(request, schedule_id):
    return HttpResponse("Schedule details %s." % schedule_id)


def event(request, event_id):
    return HttpResponse("Event %s." % event_id)
