from flow.workflow.generic import Workflow
from task.models import NetworkTask, TaskState


class CalculateMetricWorkflow(Workflow):
    flow_name = 'calculate_metric'

    def stage_0(self):
        if 'ticker' not in self.arguments:
            raise ValueError('Ticker is not defined for Finviz fundamental data collection workflow')
        task = NetworkTask.objects.create(
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
        task = NetworkTask.objects.get(id=task_id)
        return task.state == TaskState.PROCESSED

    def stage_2(self):
        task_id = self.arguments['task_id']
        task = NetworkTask.objects.get(id=task_id)
        done = append_finviz_fundamental(task)
        if done:
            task.state = TaskState.DONE
            task.postponed = now() + timedelta(days=92)
            task.save()
        return done


class CalculateAllMetricsWorkflow(Workflow):
    flow_name = 'calculate_algo_metrics'

    def stage_0(self):
        child_flow_ids: List = []
        for ticker in [ticker.symbol for ticker in Ticker.objects.all()]:
            workflow = AppendFinvizWorkflow()
            flow = workflow.create()
            workflow.arguments = {'ticker': ticker}
            child_flow_ids.append(flow.id)
            self.arguments_update({'child_flow_ids': child_flow_ids})
        self.flow.refresh_from_db()
        print(self.arguments)
        return True

    def stage_1(self):
        child_flow_ids: List = self.arguments['child_flow_ids']
        for flow_id in child_flow_ids:
            flow = Flow.objects.get(id=flow_id)
            if flow.processing_state != TaskState.DONE:
                return False
        else:
            return True

