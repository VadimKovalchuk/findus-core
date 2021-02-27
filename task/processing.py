import json

from task.models import Task
from ticker.models import Stock


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
    all_tickers = [stock.ticker for stock in Stock.objects.all()]
    missing = [ticker for ticker in json.loads(task.result) if ticker not in all_tickers]
    print(len(missing))
    for ticker_name in missing:
        # Stock(ticker=ticker_name)
        pass
    return True
