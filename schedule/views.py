from django.shortcuts import render
from django.http import HttpResponse


# Create your views here.
def index(request):
    return HttpResponse("Schedule!")


def schedule_details(request, schedule_id):
    return HttpResponse("Schedule details %s." % schedule_id)


def event(request, event_id):
    return HttpResponse("Event %s." % event_id)
