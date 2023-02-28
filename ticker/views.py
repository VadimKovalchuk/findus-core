from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic.list import ListView

from ticker.models import Ticker


# Create your views here.
def index(request):
    tickers = Ticker.objects.all()
    context = {'tickers': tickers}
    return render(request, 'ticker/index.html', context)


class TickerListView(ListView):
    model = Ticker

def ticker_base(request, ticker_pk):
    return HttpResponse("ticker intro %s." % ticker_pk)


def ticker_daily(request, ticker_pk):
    return HttpResponse("ticker price %s." % ticker_pk)


def finviz_fundamental(request, ticker_pk):
    return HttpResponse("finviz_fundamental %s." % ticker_pk)
