import datetime
import json
import logging
import traceback
import sys
import inspect

from datetime import timedelta
from time import sleep, monotonic
from typing import Callable, List, Union

from django.utils.timezone import now

from settings import log_path
from event.models import Event
from task.lib.constants import IDLE_SLEEP_TIMEOUT
from task.models import Task, SystemTask, NetworkTask
from ticker.models import Ticker, FinvizFundamental

logger = logging.getLogger('task_processor')
logger.debug(log_path)

FUNCTIONS = []


class CommonServiceMixin:
    def __init__(self):
        self.idle = False
        self._active = True

    def init_cycle(self):
        self.idle = True

    def finalize_cycle(self):
        if self.idle:
            logger.debug('Processing cycle is idle.')
            sleep(IDLE_SLEEP_TIMEOUT)

    def generic_stage_handler(self, func: Callable, task_type: str = '', task_state: str = ''):
        if task_type and task_state:
            task_limit = self.quotas[task_type][task_state]
            queue = self.queues[task_type][task_state]
            for _ in range(task_limit):
                task = next(queue)
                if task and self._active:
                    func(task)
                else:
                    return
        else:
            func()


def relay(task: Union[SystemTask, NetworkTask]):
    def extend(line: str):
        line = f'{line}, relay' if line else 'relay'
        return line
    task.arguments = extend(task.arguments)
    task.result = extend(task.result)
    task.save()
    return True


def validate_result_json(task: Task):
    logger.info(f'Validating result JSON')
    try:
        # logger.debug(type(task.result))
        # logger.debug(task.result)
        result = bool(json.loads(task.result))
        # logger.debug(f'JSON bool context: {result}')
        return True
    except TypeError:
        logger.error(f'Failed to load JSON:\n{task.arguments}')
        return False
    except KeyError:
        logger.error(f'"Ticker key is missing in task arguments when expected"')
        return False


def append_prices(task: Task):
    ticker_name = json.loads(task.arguments)['ticker']
    logger.info(f'Processing prices for {ticker_name}')
    ticker = Ticker.objects.get(symbol=ticker_name)
    history = json.loads(task.result)
    prices = history.get('prices', [])
    for price_list in prices:
        if not ticker.add_price(price_list):
            return False
    return True


def append_dividends(task: Task):
    ticker_name = json.loads(task.arguments)['ticker']
    logger.info(f'Processing dividends for {ticker_name}')
    ticker = Ticker.objects.get(symbol=ticker_name)
    history = json.loads(task.result)
    dividends = history.get('dividends', [])
    for dividend in dividends:
        if not ticker.add_dividend(dividend):
            return False
    return True


def append_finviz_fundamental(task: Task):
    ticker_name = task.arguments
    logger.info(f'Processing fundamental data from finviz for {ticker_name}')
    ticker = Ticker.objects.get(symbol=ticker_name)
    result = json.loads(task.result)
    result['values']['ticker'] = ticker
    fundamental = FinvizFundamental(**result['values'])
    fundamental.save()
    return True


def process_ticker_list(task: Task):
    all_tickers = [ticker.symbol for ticker in Ticker.objects.all()]
    missing = [ticker for ticker in json.loads(task.result) if ticker not in all_tickers]
    if len(missing):
        logger.info(f'{len(missing)} new ticker(s) found')
        parent_args = task.parent_task.result
        new_tickers = ','.join(missing)
        task.parent_task.result = f'{parent_args},{new_tickers}' if parent_args else new_tickers
        task.parent_task.save()
    return True


def new_tickers_processing(task: SystemTask):
    if not task.result:
        return True
    tickers = task.result.split(',')
    logger.info(f'{len(tickers)} new tickers found creating corresponding "new_ticker" events')
    for tkr in tickers:
        ticker = Ticker(symbol=tkr)
        ticker.save()
        task_args = json.dumps({'ticker': tkr})
        event: Event = Event(
            name='new_ticker',
            description='New ticker is created',
            artifacts=tkr,
            auto_commands='get_full_ticker_data'
        )
        event.save()
    return True


def pop_new_ticker_from_parent(task: SystemTask):
    pass


def define_ticker_daily_start_date(task: SystemTask):
    arguments = json.loads(task.arguments)
    symbol = arguments['ticker']
    ticker = Ticker.objects.get(symbol=symbol)
    if ticker.price_set.count():
        latest_price = ticker.price_set.latest('date')
        latest_date: datetime.datetime = latest_price.date
        logger.debug(f'Latest price date for {symbol}: {latest_date}')
        arguments['start'] = f'{latest_date.year}-{latest_date.month}-{latest_date.day}'
        task.arguments = json.dumps(arguments)
        task.save()
    return True


def daily_tickers_schedule(task: SystemTask):
    tickers: List[Ticker] = Ticker.objects.all()
    for ticker in tickers:
        task_args = json.dumps({'ticker': ticker.symbol})
        create_task(name='append_daily_ticker_data', parent_task=task, own_args=task_args)  # , postpone=postpone)
    return True


FUNCTIONS = {name: obj for name, obj in inspect.getmembers(sys.modules[__name__])}
