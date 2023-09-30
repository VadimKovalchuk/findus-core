from datetime import timedelta
from typing import Dict, List

from django.utils.timezone import now

from flow.workflow.generic import Workflow
from flow.models import Flow
from task.models import Task, TaskState
from task.lib.processing import (append_prices, append_dividends, append_finviz_fundamental, append_new_tickers,
                                 update_scope, define_ticker_daily_start_date)
from ticker.models import Ticker


class ScopeUpdateWorkflow(Workflow):
    flow_name = 'update_ticker_list'

    def stage_0(self):
        task_ids = []
        for scope_name in ["SP500", "SP400", "SP600"]:
            task = Task.objects.create(
                name=f'update_{scope_name.lower()}_ticker_list',
                flow=self.flow,
                module='findus_edge.tickers',
                function='get_scope',
            )
            task.arguments_dict = {"scope": scope_name}
            task.save()
            task_ids.append(task.id)
        self.arguments_update({'task_ids': task_ids})
        return True

    def stage_1(self):
        task_ids = self.flow.arguments_dict['task_ids']
        for task_id in task_ids:
            task = Task.objects.get(id=task_id)
            if task.state != TaskState.PROCESSED:
                return False
        else:
            return True

    def stage_2(self):
        task_ids = self.arguments['task_ids']
        all_pass = True
        for task_id in task_ids:
            task = Task.objects.get(id=task_id)
            if task.state == TaskState.PROCESSED:
                if append_new_tickers(task) and update_scope(task):
                    task.state = TaskState.DONE
                    task.postponed = now() + timedelta(days=92)
                    task.save()
                else:
                    all_pass = False
        return all_pass


class AppendTickerPricesWorfklow(Workflow):
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
        self.arguments_update({'task_id': task.id})
        return True

    def stage_1(self):
        task_id = self.arguments['task_id']
        task = Task.objects.get(id=task_id)
        return task.state == TaskState.PROCESSED

    def stage_2(self):
        task_id = self.arguments['task_id']
        task = Task.objects.get(id=task_id)
        done = append_prices(task) and append_dividends(task)
        if done:
            task.state = TaskState.DONE
            task.postponed = now() + timedelta(days=92)
            task.save()
        return done


class AddAllTickerPricesWorkflow(Workflow):
    flow_name = 'collect_daily_global'

    def stage_0(self):
        child_flow_ids: List = []
        for ticker in [ticker.symbol for ticker in Ticker.objects.all()]:
            workflow = AppendTickerPricesWorfklow()
            flow = workflow.create()
            workflow.arguments = {'ticker': ticker}
            child_flow_ids.append(flow.id)
            self.arguments_update({'child_flow_ids': child_flow_ids})
        self.flow.refresh_from_db()
        # print(self.arguments)
        return True

    def stage_1(self):
        child_flow_ids: List = self.arguments['child_flow_ids']
        for flow_id in child_flow_ids:
            flow = Flow.objects.get(id=flow_id)
            if flow.processing_state != TaskState.DONE:
                return False
        else:
            return True


class AppendFinvizWorkflow(Workflow):
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
        self.arguments_update({'task_id': task.id})
        return True

    def stage_1(self):
        task_id = self.arguments['task_id']
        task = Task.objects.get(id=task_id)
        return task.state == TaskState.PROCESSED

    def stage_2(self):
        task_id = self.arguments['task_id']
        task = Task.objects.get(id=task_id)
        done = append_finviz_fundamental(task)
        if done:
            task.state = TaskState.DONE
            task.postponed = now() + timedelta(days=92)
            task.save()
        return done


class AddAllTickerFinvizWorkflow(Workflow):
    flow_name = 'collect_finviz_fundamental_global'

    def stage_0(self):
        child_flow_ids: List = []
        for ticker in [ticker.symbol for ticker in Ticker.objects.all()]:
            workflow = AppendFinvizWorkflow()
            flow = workflow.create()
            workflow.arguments = {'ticker': ticker}
            child_flow_ids.append(flow.id)
            self.arguments_update({'child_flow_ids': child_flow_ids})
        self.flow.refresh_from_db()
        # print(self.arguments)
        return True

    def stage_1(self):
        child_flow_ids: List = self.arguments['child_flow_ids']
        for flow_id in child_flow_ids:
            flow = Flow.objects.get(id=flow_id)
            if flow.processing_state != TaskState.DONE:
                return False
        else:
            return True
