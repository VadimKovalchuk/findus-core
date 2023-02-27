from django.shortcuts import render

from django.http import HttpResponse


# Create your views here.
def index(request):
    return HttpResponse("Tickers!")


def ticker_base(request, ticker_id):
    return HttpResponse("ticker intro %s." % ticker_id)


def ticker_daily(request, ticker):
    return HttpResponse("ticker price %s." % ticker)


def finviz_fundamental(request, ticker):
    return HttpResponse("finviz_fundamental %s." % ticker)
