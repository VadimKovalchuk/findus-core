from flow.models import FlowState
from task.models import Task, TaskState


FLOW_PROCESSING_QUOTAS = {
    FlowState.CREATED: 1,
    FlowState.RUNNING: 10,
    FlowState.DONE: 1,
    FlowState.POSTPONED: 100
}
TASK_PROCESSING_QUOTAS = {
    TaskState.CREATED: 2,
    TaskState.STARTED: 2,
    TaskState.PROCESSED: 4,
    TaskState.DONE: 1,
    TaskState.POSTPONED: 100,
    'overdue': 100,
}
