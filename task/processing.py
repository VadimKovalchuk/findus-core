import json
import logging
from typing import List, Union

from django.utils.timezone import now

from task.commands import commands
from task.models import Task, SystemTask, NetworkTask
from ticker.models import Ticker

logger = logging.getLogger(__name__)


def get_function(name: str):
    functions = {
        append_daily_data.__name__: append_daily_data,
        process_ticker_list.__name__: process_ticker_list
    }
    return functions[name]


def create_task(name: str, parent_task: SystemTask = None):
    command = commands[name]
    if command['dcn_task']:
        task: NetworkTask = NetworkTask.objects.create(name=name)
        task.module = command['module']
        task.function = command['function']
    else:
        task = SystemTask.objects.create(name=name)
    if parent_task:
        task.priority = parent_task.priority
        task.arguments = parent_task.arguments
        task.parent_task = parent_task
        logger.debug([parent_task.systemtask_set.all(), parent_task.networktask_set.all()])
    on_start = get_function(command['run_on_start'])(task) if command['run_on_start'] else True
    if not on_start:
        raise SystemError(f'Command {name} on_start flow failed')
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
    return query_set


def start_task(task: List[SystemTask]):
    child_tasks = commands[task.name]['child_tasks']
    if child_tasks:
        for task_name in child_tasks:
            create_task(task_name, task)
    task.started = now()
    task.save()


def get_postponed_tasks() -> List[SystemTask]:
    query_set = SystemTask.objects.filter(started__isnull=False)
    query_set = query_set.filter(done__isnull=True)
    query_set = query_set.filter(postponed__isnull=False)
    return query_set


def trigger_postponed_task(task: List[SystemTask]):
    pass


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
