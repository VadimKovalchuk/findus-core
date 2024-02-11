from algo.models import Algo
from algo.algorithm import get_algorithm_map
from flow.workflow.constants import DEFAULT_SCOPES
from flow.workflow.generic import Workflow
from ticker.models import Scope


class DefaultScopesWorkflow(Workflow):
    flow_name = 'create_default_scopes'

    def stage_0(self):
        scope_name_list = DEFAULT_SCOPES
        for scope_name in scope_name_list:
            if not Scope.objects.filter(name=scope_name):
                scope = Scope.objects.create(name=scope_name)
                scope.save()
        return True


class DefaultAlgorithmsWorkflow(Workflow):
    flow_name = 'create_default_algos'

    def stage_0(self):
        algo_name_list = ['finviz_initial_algorithm']
        algorithm_map = get_algorithm_map()
        for algo_name in algo_name_list:
            if not Algo.objects.filter(name=algo_name):
                algorythm = algorithm_map.get(algo_name)
                algorythm().deploy()
        return True
