import sys
import inspect
from flow.workflow.test import *
from flow.workflow.generic import *


def get_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        classes = []
        print(obj)
        if inspect.isclass(obj):
            classes.append(obj)
