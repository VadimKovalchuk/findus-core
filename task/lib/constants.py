from flow.models import FlowState
from task.models import NetworkTask, SystemTask, TaskState


class TaskType:
    Network = NetworkTask.__name__
    System = SystemTask.__name__
    ALL = (Network, System)


IDLE_SLEEP_TIMEOUT = 10  # seconds
FLOW_PROCESSING_QUOTAS = {
    FlowState.CREATED: 1,
    FlowState.RUNNING: 4,
    FlowState.DONE: 1,
    FlowState.POSTPONED: 100
}
TASK_PROCESSING_QUOTAS = {
    TaskState.CREATED: 2,
    TaskState.STARTED: 2,
    TaskState.PROCESSED: 4,
    TaskState.DONE: 1,
    TaskState.POSTPONED: 100
}
