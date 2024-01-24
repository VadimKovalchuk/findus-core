from flow.workflow.algo import *
from flow.workflow.collection import *
from flow.workflow.infra import *
from flow.workflow.test import *
from flow.workflow.generic import Workflow


def get_workflow_map():
    class_map = {}
    classes = Workflow.__subclasses__()
    classes.append(Workflow)
    for _class in classes:
        class_map[_class.flow_name] = _class
    return class_map
