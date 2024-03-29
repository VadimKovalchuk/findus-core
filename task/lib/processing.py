import datetime
import json
import logging
import sys
import inspect
from typing import Union

from django.db import transaction

from settings import log_path
from schedule.lib.interface import Scheduler
from task.models import Task
from ticker.models import Ticker, FinvizFundamental, Scope

logger = logging.getLogger('task_processor')
logger.debug(log_path)


def validate_result_json(task: Task):
    logger.info(f'Validating result JSON')
    try:
        # result = bool(json.loads(task.result))
        # logger.debug(f'JSON bool context: {result}')
        return True
    except TypeError:
        logger.error(f'Failed to load JSON:\n{task.arguments}')
        return False
    except KeyError:
        logger.error(f'"Ticker key is missing in task arguments when expected"')
        return False


def append_prices(task: Task):
    ticker_name = task.arguments_dict['ticker']
    logger.info(f'Processing prices for {ticker_name}')
    ticker = Ticker.objects.get(symbol=ticker_name)
    history = task.result_dict
    prices = history.get('prices', [])
    for price_list in prices:
        if not ticker.add_price(price_list):
            return False
    return True


def append_dividends(task: Task):
    ticker_name = task.arguments_dict['ticker']
    logger.info(f'Processing dividends for {ticker_name}')
    ticker = Ticker.objects.get(symbol=ticker_name)
    history = task.result_dict
    dividends = history.get('dividends', [])
    for dividend in dividends:
        if not ticker.add_dividend(dividend):
            return False
    return True


def append_finviz_fundamental(task: Task):
    ticker_name = task.arguments_dict['ticker']
    logger.info(f'Processing fundamental data from finviz for {ticker_name}')
    ticker = Ticker.objects.get(symbol=ticker_name)
    result = task.result_dict
    result['values']['ticker'] = ticker
    fundamental = FinvizFundamental(**result['values'])
    fundamental.save()
    return True


def append_new_tickers(task: Task):
    all_tickers = [ticker.symbol for ticker in Ticker.objects.all()]
    missing = [ticker for ticker in task.result_dict if ticker not in all_tickers]
    if len(missing):
        logger.info(f'{len(missing)} new ticker(s) found')
        for tkr in missing:
            if len(tkr) > 6:
                logger.error(f"Suspicious ticker name: {tkr}")
                # TODO: Handle via event
                continue
            with transaction.atomic():
                # logger.debug(tkr)
                ticker = Ticker(symbol=tkr)
                ticker.save()
                # scheduler: Scheduler = Scheduler(event_name='new_ticker', artifacts=json.dumps({"ticker": tkr}))
                # scheduler.push()
    return True


def update_scope(task: Task):
    reference_tkr_list = task.result_dict
    logger.debug(task.arguments_dict)
    arguments = task.arguments_dict
    scope_name = arguments.get("scope")
    scope = Scope.objects.get(name=scope_name)
    scope_tickers = [ticker.symbol for ticker in scope.tickers.all()]
    missing = [ticker for ticker in reference_tkr_list if ticker not in scope_tickers]
    if missing:
        logger.info(f'{len(missing)} new tickers will be added to scope "{scope_name}"')
        for tkr in missing:
            ticker = Ticker.objects.get(symbol=tkr)
            scope.tickers.add(ticker)
            scope.save()
            # scheduler: Scheduler = Scheduler(event_name='scope_add', artifacts=json.dumps({"ticker": tkr}))
            # scheduler.push()
    redundant = [ticker for ticker in scope_tickers if ticker not in reference_tkr_list]
    if redundant:
        logger.info(f'{len(redundant)} tickers will be removed from scope "{scope_name}"')
        for tkr in redundant:
            ticker = Ticker.objects.get(symbol=tkr)
            logger.debug(ticker)
            scope.tickers.remove(ticker)
            scope.save()
            # scheduler: Scheduler = Scheduler(event_name='scope_exclude', artifacts=json.dumps({"ticker": tkr}))
            # scheduler.push()
    return True


def get_all_tickers(task: Task):
    arguments = task.arguments_dict
    tickers = Ticker.objects.all()
    symbols = [ticker.symbol for ticker in tickers]
    arguments["ticker"] = symbols
    task.arguments_dict = arguments
    task.save()
    return True


def clone_arguments_to_children(task):
    if task.arguments:
        for child_task in task.get_children():
            child_task.arguments = task.arguments
            child_task.save()
    else:
        logger.warning(f'No arguments to clone from task: {task}')
    return True


def define_ticker_daily_start_date(task: Task):
    arguments = task.arguments_dict
    symbol = arguments['ticker']
    ticker = Ticker.objects.get(symbol=symbol)
    if ticker.price_set.count():
        latest_price = ticker.price_set.latest('date')
        latest_date: datetime.datetime = latest_price.date + datetime.timedelta(days=1)
        logger.debug(f'Latest price date for {symbol}: {latest_date}')
        arguments['start'] = f'{latest_date.year}-{latest_date.month}-{latest_date.day}'
        task.arguments_dict = arguments
        task.save()
    return True


def draft_get_param_for_algo(task: Task):
    with open('pe.txt', 'w') as fh:
        for tkr in tkrs:
            fv = tkr.finvizfundamental_set.first()
            if fv and fv.price_earnings:
                line = f"{tkr.symbol},{fv.price_earnings}\n"
                fh.write(line)


PROCESSING_FUNCTIONS = {name: obj for name, obj in inspect.getmembers(sys.modules[__name__])}
