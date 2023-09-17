from datetime import timedelta
from typing import Dict

from django.utils.timezone import now

from flow.workflow.generic import Workflow
from task.models import NetworkTask, TaskState
from task.lib.processing import (append_prices, append_dividends, append_new_tickers, update_scope,
                                 define_ticker_daily_start_date)


class ScopeUpdateWorklow(Workflow):
    flow_name = 'update_ticker_list'

    def stage_0(self):
        task_ids = []
        for scope_name in ["SP500", "SP400", "SP600"]:
            task = NetworkTask.objects.create(
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
            task = NetworkTask.objects.get(id=task_id)
            if task.state != TaskState.PROCESSED:
                return False
        else:
            return True

    def stage_2(self):
        task_ids = self.arguments['task_ids']
        all_pass = True
        for task_id in task_ids:
            task = NetworkTask.objects.get(id=task_id)
            if task.state == TaskState.PROCESSED:
                if append_new_tickers(task) and update_scope(task):
                    task.state = TaskState.DONE
                    task.postponed = now() + timedelta(days=92)
                    task.save()
                else:
                    all_pass = False
        return all_pass


class AppendTickerPricesWorklow(Workflow):
    flow_name = 'append_ticker_price_data'

    def stage_0(self):
        if 'ticker' not in self.arguments:
            raise ValueError('Ticker is not defined for prices collection workflow')
        task = NetworkTask.objects.create(
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
        task = NetworkTask.objects.get(id=task_id)
        return task.state == TaskState.PROCESSED

    def stage_2(self):
        task_id = self.arguments['task_id']
        task = NetworkTask.objects.get(id=task_id)
        return append_prices(task) and append_dividends(task)
