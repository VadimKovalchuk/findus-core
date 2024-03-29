from datetime import timedelta
from typing import Dict, List

from django.utils.timezone import now

from flow.workflow.generic import Workflow, TaskHandler, ChildWorkflowHandler
from flow.models import Flow
from task.models import Task, TaskState
from task.lib.processing import (append_prices, append_dividends, append_finviz_fundamental, append_new_tickers,
                                 update_scope, define_ticker_daily_start_date)
from ticker.models import Ticker


class ScopeUpdateWorkflow(Workflow, TaskHandler):
    flow_name = 'update_ticker_list'

    def stage_0(self):
        for scope_name in ["SP500", "SP400", "SP600"]:
            task = Task.objects.create(
                name=f'update_{scope_name.lower()}_ticker_list',
                flow=self.flow,
                module='findus_edge.tickers',
                function='get_scope',
            )
            task.arguments_dict = {"scope": scope_name}
            task.save()
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):
        return self.map_task_results([append_new_tickers, update_scope])


class AppendTickerPricesWorfklow(Workflow, TaskHandler):
    flow_name = 'append_ticker_price_data'

    def stage_0(self):
        if 'ticker' not in self.arguments:
            raise ValueError('Ticker is not defined for prices collection workflow')
        task = Task.objects.create(
            name='get_ticker_prices',
            flow=self.flow,
            module='findus_edge.yahoo',
            function='ticker_history',
        )
        task.arguments_dict = {'ticker': self.arguments['ticker']}
        task.save()
        define_ticker_daily_start_date(task)  # TODO: REFACTOR!
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):
        return self.map_task_results([append_prices, append_dividends])


class AddAllTickerPricesWorkflow(Workflow, ChildWorkflowHandler):
    flow_name = 'collect_daily_prices_global'

    def stage_0(self):
        for ticker in [ticker.symbol for ticker in Ticker.objects.all()]:
            workflow = AppendTickerPricesWorfklow()
            flow = workflow.create()
            workflow.arguments = {'ticker': ticker}
            self.append_child_flow(flow)
        return True

    def stage_1(self):
        return self.check_child_flows_done()


class AppendFinvizWorkflow(Workflow, TaskHandler):
    flow_name = 'append_finviz_fundamental'

    def stage_0(self):
        if 'ticker' not in self.arguments:
            raise ValueError('Ticker is not defined for Finviz fundamental data collection workflow')
        task = Task.objects.create(
            name='append_finviz_fundamental',
            flow=self.flow,
            module='findus_edge.finviz',
            function='fundamental_converted',
        )
        task.arguments_dict = {'ticker': self.arguments['ticker']}
        task.save()
        return True

    def stage_1(self):
        return self.check_all_task_processed()

    def stage_2(self):
        return self.map_task_results([append_finviz_fundamental])


class AddAllTickerFinvizWorkflow(Workflow, ChildWorkflowHandler):
    flow_name = 'collect_finviz_fundamental_global'

    def stage_0(self):
        for ticker in [ticker.symbol for ticker in Ticker.objects.all()]:
            workflow = AppendFinvizWorkflow()
            flow = workflow.create()
            workflow.arguments = {'ticker': ticker}
            self.append_child_flow(flow)
        return True

    def stage_1(self):
        return self.check_child_flows_done()
