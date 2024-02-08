import json
import logging

from datetime import datetime, timedelta
from typing import Dict, List

from django.db import transaction
from django.utils.timezone import now

from flow.workflow.constants import DEFAULT_START_DATE, DISABLE_EVENTS, CHILDREN_DISTRIBUTION, REQUEUE_PERIOD
from flow.workflow.generic import Workflow, TaskHandler, ChildWorkflowHandler
from schedule.lib.interface import Scheduler
from task.models import Task
from task.lib.processing import update_scope
from ticker.models import Ticker, FinvizFundamental


logger = logging.getLogger('flow_processor')


class ScopeUpdateWorkflow(Workflow, TaskHandler):
    flow_name = 'update_ticker_list'

    def set_for_test(self):
        self.update_arguments({
            REQUEUE_PERIOD: 0,
            DISABLE_EVENTS: True,
        })
        self.save()

    def stage_0(self):
        for scope_name in ["SP500", "SP400", "SP600"]:
            arguments = {"scope": scope_name}
            task = Task.objects.create(
                name=f'update_{scope_name.lower()}_ticker_list',
                flow=self.flow,
                module='findus_edge.tickers',
                function='get_scope',
                arguments=json.dumps(arguments),
            )
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):

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
                        ticker = Ticker(symbol=tkr)
                        ticker.save()
                        if active_events:
                            scheduler: Scheduler = Scheduler(event_name='new_ticker', artifacts=json.dumps({"ticker": tkr}))
                            scheduler.push()
            return True

        active_events = False if DISABLE_EVENTS in self.arguments and self.arguments[DISABLE_EVENTS] is True else True
        return self.map_task_results([append_new_tickers, update_scope])


class AppendTickerPricesWorfklow(Workflow, TaskHandler):
    flow_name = 'append_ticker_price_data'

    def set_for_test(self):
        self.update_arguments({REQUEUE_PERIOD: 0})
        self.save()

    def stage_0(self):
        def define_ticker_daily_start_date(symbol: str):
            ticker = Ticker.objects.get(symbol=symbol)
            if ticker.price_set.count():
                latest_price = ticker.price_set.latest('date')
                latest_date = latest_price.date + timedelta(days=1)
                logger.debug(f'Latest price date for {ticker.symbol}: {latest_date}')
                return f'{latest_date.year}-{latest_date.month}-{latest_date.day}'
            else:
                return DEFAULT_START_DATE

        if 'ticker' not in self.arguments:
            raise ValueError('Ticker is not defined for prices collection workflow')
        symbol = self.arguments['ticker']
        arguments = {
            'ticker': symbol,
            'start': define_ticker_daily_start_date(symbol),
        }
        task = Task.objects.create(
            name='get_ticker_prices',
            flow=self.flow,
            module='findus_edge.yahoo',
            function='ticker_history',
            arguments=json.dumps(arguments),
        )
        return True

    def stage_1(self):
        if self.check_all_task_processed():
            return True
        else:
            self.postpone_requeue()
            return False

    def stage_2(self):

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

        return self.map_task_results([append_prices, append_dividends])


class AddAllTickerPricesWorkflow(Workflow, ChildWorkflowHandler):
    flow_name = 'collect_daily_prices_global'

    def set_for_test(self):
        self.update_arguments({REQUEUE_PERIOD: 0})
        self.save()

    def stage_0(self):
        logger.info('Creating child workflows')
        for ticker in [ticker.symbol for ticker in Ticker.objects.all()]:
            workflow = AppendTickerPricesWorfklow()
            flow = workflow.create()
            workflow.arguments = {'ticker': ticker}
            self.append_child_flow(flow)
            if REQUEUE_PERIOD in self.arguments:  # Custom requeue period for testing purposes
                workflow.update_arguments({REQUEUE_PERIOD: self.arguments[REQUEUE_PERIOD]})
        return True

    def stage_1(self):
        if self.check_child_flows_done():
            return True
        else:
            self.postpone_requeue()
            return False


class AppendFinvizWorkflow(Workflow, TaskHandler):
    flow_name = 'append_finviz_fundamental'

    def set_for_test(self):
        self.update_arguments({REQUEUE_PERIOD: 0})
        self.save()

    def stage_0(self):
        if 'ticker' not in self.arguments:
            raise ValueError('Ticker is not defined for Finviz fundamental data collection workflow')
        arguments = {'ticker': self.arguments['ticker']}
        task = Task.objects.create(
            name='append_finviz_fundamental',
            flow=self.flow,
            module='findus_edge.finviz',
            function='fundamental_converted',
            arguments=json.dumps(arguments),
        )
        return True

    def stage_1(self):
        if self.check_all_task_processed():
            return True
        else:
            self.postpone_requeue()
            return False

    def stage_2(self):

        def append_finviz_fundamental(task: Task):
            ticker_name = task.arguments_dict['ticker']
            logger.info(f'Processing fundamental data from finviz for {ticker_name}')
            ticker = Ticker.objects.get(symbol=ticker_name)
            result = task.result_dict
            result['values']['ticker'] = ticker
            fundamental = FinvizFundamental(**result['values'])
            fundamental.save()
            return True

        return self.map_task_results([append_finviz_fundamental])


class AddAllTickerFinvizWorkflow(Workflow, ChildWorkflowHandler):
    flow_name = 'collect_finviz_fundamental_global'

    def set_for_test(self):
        self.update_arguments({
            REQUEUE_PERIOD: 0,
            CHILDREN_DISTRIBUTION: (0, 0),
        })
        self.save()

    def stage_0(self):
        logger.info('Creating child workflows')
        for ticker in [ticker.symbol for ticker in Ticker.objects.all()]:
            workflow = AppendFinvizWorkflow()
            flow = workflow.create()
            workflow.arguments = {'ticker': ticker}
            self.append_child_flow(flow)
            if REQUEUE_PERIOD in self.arguments:  # Custom requeue period for testing purposes
                workflow.update_arguments({REQUEUE_PERIOD: self.arguments[REQUEUE_PERIOD]})
        # Custom values for children distribution on timeline
        start_delay, step = self.arguments[CHILDREN_DISTRIBUTION] if CHILDREN_DISTRIBUTION in self.arguments else (20, 1)
        self.distribute_children_on_timeline(start_delay, step)
        return True

    def stage_1(self):
        if self.check_child_flows_done():
            return True
        else:
            self.postpone_requeue()
            return False


class NewTickerProcessingWorkflow(Workflow, ChildWorkflowHandler):
    flow_name = 'get_new_ticker_data'

    def set_for_test(self):
        self.update_arguments({
            REQUEUE_PERIOD: 0,
        })
        self.save()

    def stage_0(self):
        if 'ticker' not in self.arguments:
            raise ValueError('Ticker is not defined for Finviz fundamental data collection workflow')
        arguments = {'ticker': self.arguments['ticker']}
        logger.info('Creating child workflows')
        for workflow_class in (AppendTickerPricesWorfklow, AppendFinvizWorkflow,):
            workflow = workflow_class()
            flow = workflow.create()
            workflow.arguments = arguments
            self.append_child_flow(flow)
            if REQUEUE_PERIOD in self.arguments:  # Custom requeue period for testing purposes
                workflow.update_arguments({REQUEUE_PERIOD: self.arguments[REQUEUE_PERIOD]})
        return True

    def stage_1(self):
        if self.check_child_flows_done():
            return True
        else:
            self.postpone_requeue()
            return False
