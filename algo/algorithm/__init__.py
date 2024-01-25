from algo.algorithm.generic import Algorithm
from algo.algorithm.test import *


def get_algorithm_map():
    class_map = {}
    classes = Algorithm.__subclasses__()
    classes.append(Algorithm)
    for _class in classes:
        class_map[_class.name] = _class
    return class_map
