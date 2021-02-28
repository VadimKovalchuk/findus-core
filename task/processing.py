import json

from task.models import Task
from ticker.models import Ticker


def get_function(name: str):
    functions = {
        append_daily_data.__name__: append_daily_data,
        process_ticker_list.__name__: process_ticker_list
    }
    return functions[name]


def append_daily_data(task: Task):
    return True


def append_fundamentals(task: Task):
    return True


def process_ticker_list(task: Task):
    all_tickers = [ticker.symbol for ticker in Ticker.objects.all()]
    missing = [ticker for ticker in json.loads(task.result) if ticker not in all_tickers]
    print(len(missing))
    for ticker_name in missing:
        ticker = Ticker(symbol=ticker_name)
        ticker.save()
    return True
