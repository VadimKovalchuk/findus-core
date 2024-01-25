from flow.workflow.generic import Workflow
from ticker.models import Scope


class DefaultScopesWorkflow(Workflow):
    flow_name = 'create_default_scopes'

    def stage_0(self):
        scope_name_list = ["SP500", "SP400", "SP600"]  # extend with SCHD
        for scope_name in scope_name_list:
            if not Scope.objects.filter(name=scope_name):
                scope = Scope.objects.create(name=scope_name)
                scope.save()
        return True
