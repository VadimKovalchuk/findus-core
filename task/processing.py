import datetime
import json
import logging
import traceback

from datetime import timedelta
from typing import List, Union

from django.utils.timezone import now

from settings import log_path
from task.commands import commands
from task.models import Task, SystemTask, NetworkTask
from ticker.models import Ticker, Price, Dividend

logger = logging.getLogger('task_processor')
logger.debug(log_path)


def get_function(name: str):
    functions = {
        append_daily_data.__name__: append_daily_data,
        # convert_args_for_dcn.__name__: convert_args_for_dcn,
        daily_collection_start_date.__name__: daily_collection_start_date,
        daily_tickers_schedule.__name__: daily_tickers_schedule,
        new_tickers_processing.__name__: new_tickers_processing,
        process_ticker_list.__name__: process_ticker_list
    }
    return functions.get(name)


def create_task(name: str, parent_task: SystemTask = None, own_args: str = '', postpone: int = 0):
    logger.debug(f'Creating task: {name}')
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
        logger.debug(f'Task is created by parent: {parent_task.name} ({parent_task.id})')
        task.parent_task = parent_task
        task.priority = parent_task.priority
        if not own_args and parent_task.arguments:
            task.arguments = parent_task.arguments
        # logger.debug([parent_task.systemtask_set.all(), parent_task.networktask_set.all()])
    if command['run_on_start']:
        on_start_function = get_function(command['run_on_start'])
        try:
            on_start_result = on_start_function(task)
        except Exception as err:
            logger.error(f'{err.args}\n{traceback.format_exc()}')
            on_start_result = False
        if not on_start_result:
            task.delete()
            raise SystemError(f'Command {name} "on_start" flow failed')
    if postpone:
        task.postponed = now() + timedelta(seconds=postpone)
    task.save()
    logger.info(f'Created: {task}')


def get_done_network_tasks() -> List[NetworkTask]:
    query_set = NetworkTask.objects.filter(done__isnull=False)
    query_set = query_set.filter(processed__isnull=True)
    query_set = query_set.order_by('done')
    tasks = [query_set.first()]
    return [task for task in tasks if task]


def search_tasks_with_completed_child(tasks: List[SystemTask]) -> List[SystemTask]:
    pass


def finalize_task(task: Union[SystemTask, NetworkTask]):
    logger.info(f'Finalizing task "{task.name}"({task.id})')
    command = commands[task.name]
    on_done = get_function(command['run_on_done'])(task) if command['run_on_done'] else True
    if not on_done:
        task.done = now()
        task.save()
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


def get_new_system_tasks() -> List[SystemTask]:
    query_set = SystemTask.objects.filter(started__isnull=True)
    query_set = query_set.filter(postponed__isnull=True)
    query_set = query_set.order_by('created')
    tasks = [query_set.first()]
    return [task for task in tasks if task]


def start_task(task: SystemTask):
    child_tasks = commands[task.name]['child_tasks']
    logger.debug(f'Task "{task.name}" has {len(child_tasks)} child tasks')
    if child_tasks:
        for task_name in child_tasks:
            create_task(task_name, task)
    task.started = now()
    task.save()


def get_postponed_tasks() -> List[SystemTask]:
    query_set = SystemTask.objects.filter(started__isnull=True)
    query_set = query_set.filter(postponed__gt=now())
    query_set = query_set.order_by('postponed')
    tasks = [query_set.first()]
    return [task for task in tasks if task]


def trigger_postponed_task(task: List[SystemTask]):
    pass


def append_daily_data(task: Task):
    try:
        ticker_name = json.loads(task.arguments)['ticker']
    except TypeError:
        logger.error(f'Failed to load JSON:\n{task.arguments}')
        return False
    except KeyError:
        logger.error(f'"Ticker key is missing in task arguments when expected"')
        return False
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


# def convert_args_for_dcn(task: NetworkTask):
#     str_args = task.arguments
#     task.arguments = json.dumps({'ticker': str_args})
#     task.save()
#     return True


def new_tickers_processing(task: SystemTask):
    if not task.arguments:
        return True
    tickers = task.arguments.split(',')
    task.result = task.arguments
    task.arguments = None
    task.save()
    postpone = 0
    for tkr in tickers:
        task_args = json.dumps({'ticker': tkr})
        create_task(name='get_full_ticker_data', parent_task=task, own_args=task_args)  # , postpone=postpone)
        postpone += 1  # seconds
    return True


def daily_collection_start_date(task: SystemTask):
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
