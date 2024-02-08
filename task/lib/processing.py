import logging

from django.db import transaction

from settings import log_path
from schedule.lib.interface import Scheduler
from task.models import Task
from ticker.models import Ticker, Scope

logger = logging.getLogger('processing')


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
