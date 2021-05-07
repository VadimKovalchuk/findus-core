import datetime
import json
import logging

from datetime import timedelta
from typing import List, Union

from django.utils.timezone import now

from task.commands import commands
from task.models import Task, SystemTask, NetworkTask
from ticker.models import Ticker, Price, Dividend

logger = logging.getLogger(__name__)


def get_function(name: str):
    functions = {
        append_daily_data.__name__: append_daily_data,
        convert_args_for_dcn.__name__: convert_args_for_dcn,
        daily_collection_start_date.__name__: daily_collection_start_date,
        new_tickers_processing.__name__: new_tickers_processing,
        process_ticker_list.__name__: process_ticker_list
    }
    return functions[name]


def create_task(name: str, parent_task: SystemTask = None, own_args: str = '', postpone: int = 0):
    command = commands[name]
    if command['dcn_task']:
        task: NetworkTask = NetworkTask.objects.create(name=name)
        task.module = command['module']
        task.function = command['function']
    else:
        task = SystemTask.objects.create(name=name)
    if own_args:
        task.arguments = own_args
    if parent_task:
        task.parent_task = parent_task
        task.priority = parent_task.priority
        if not own_args and parent_task.arguments:
            task.arguments = parent_task.arguments
        logger.debug([parent_task.systemtask_set.all(), parent_task.networktask_set.all()])
    on_start = get_function(command['run_on_start'])(task) if command['run_on_start'] else True
    if not on_start:
        task.delete()
        raise SystemError(f'Command {name} "on_start" flow failed')
    if postpone:
        task.postponed = now() + timedelta(seconds=postpone)
    task.save()
    logger.info(f'Created: {task}')


def get_done_network_tasks() -> List[NetworkTask]:
    query_set = NetworkTask.objects.filter(done__isnull=False)
    query_set = query_set.filter(processed__isnull=True)
    return query_set


def search_tasks_with_completed_child(tasks: List[SystemTask]) -> List[SystemTask]:
    pass


def finalize_task(task: Union[SystemTask, NetworkTask]):
    command = commands[task.name]
    on_done = get_function(command['run_on_done'])(task) if command['run_on_done'] else True
    if not on_done:
        raise SystemError(f'Command {task.name} on_done flow failed')
    if isinstance(task, SystemTask) and not task.is_done():
        return
    if not task.done:
        task.done = now()
    task.processed = now()
    task.save()
    logger.info(f'{task} processing completed')
    if task.parent_task and task.parent_task.is_done():
        finalize_task(task.parent_task)


def get_new_tasks() -> List[SystemTask]:
    query_set = SystemTask.objects.filter(started__isnull=True)
    query_set = query_set.filter(postponed__isnull=True)
    return query_set


def start_task(task: List[SystemTask]):
    child_tasks = commands[task.name]['child_tasks']
    if child_tasks:
        for task_name in child_tasks:
            create_task(task_name, task)
    task.started = now()
    task.save()


def get_postponed_tasks() -> List[SystemTask]:
    query_set = SystemTask.objects.filter(postponed__gt=now())
    return query_set


def trigger_postponed_task(task: List[SystemTask]):
    pass


def append_daily_data(task: Task):
    ticker_name = json.loads(task.arguments)['ticker']
    logger.info(f'Processing prices and dividends for {ticker_name}')
    ticker = Ticker.objects.get(symbol=ticker_name)
    history = json.loads(task.result)
    prices = history.get('prices', [])
    for price_list in prices:
        date, _open, high, low, close, volume = price_list
        if len(ticker.price_set.filter(date=date)):
            logger.debug(f'{ticker_name} price for {date} already exists')
        else:
            Price.objects.create(ticker=ticker, date=date, open=_open, high=high, low=low, close=close, volume=volume)
    dividends = history.get('dividends', [])
    for dividend in dividends:
        date, size = dividend
        if len(ticker.dividend_set.filter(date=date)):
            logger.debug(f'{ticker_name} dividend for {date} already exists')
        else:
            Dividend.objects.create(ticker=ticker, date=date, size=size)
    return True


def append_fundamentals(task: Task):
    return True


def process_ticker_list(task: Task):
    all_tickers = [ticker.symbol for ticker in Ticker.objects.all()]
    missing = [ticker for ticker in json.loads(task.result) if ticker not in all_tickers]
    if len(missing):
        logger.info(f'{len(missing)} new ticker(s) found')
        for ticker_name in missing:
            ticker = Ticker(symbol=ticker_name)
            ticker.save()
        parent_args = task.parent_task.arguments
        new_tickers = ','.join(missing)
        task.parent_task.arguments = f'{parent_args},{new_tickers}' if parent_args else new_tickers
        task.parent_task.save()
    return True


def convert_args_for_dcn(task: NetworkTask):
    str_args = task.arguments
    task.arguments = json.dumps({'ticker': str_args})
    task.save()
    return True


def new_tickers_processing(task: SystemTask):
    if not task.arguments:
        return True
    tickers = task.arguments.split(',')
    task.result = task.arguments
    task.arguments = None
    task.save()
    postpone = 0
    for tkr in tickers:
        create_task(name='get_full_ticker_data', parent_task=task, own_args=tkr)  # , postpone=postpone)
        postpone += 1  # seconds
    return True


def daily_collection_start_date(task: SystemTask):
    arguments = json.loads(task.arguments)
    symbol = arguments['ticker']
    ticker = Ticker.objects.get(symbol=symbol)
    latest_price = ticker.price_set.latest('date')
    latest_date: datetime.datetime = latest_price.date
    logger.debug(f'Latest price date for {symbol}: {latest_date}')
    arguments['start'] = f'{latest_date.year}-{latest_date.month}-{latest_date.day}'
    task.arguments = json.dumps(arguments)
    task.save()
    return True
