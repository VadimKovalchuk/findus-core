from flow.models import FlowState
from task.models import Task, TaskState


FLOW_PROCESSING_QUOTAS = {
    FlowState.CREATED: 1,
    FlowState.RUNNING: 4,
    FlowState.DONE: 1,
    FlowState.POSTPONED: 10
}
TASK_PROCESSING_QUOTAS = {
    TaskState.CREATED: 2,
    TaskState.STARTED: 2,
    TaskState.PROCESSED: 4,
    TaskState.DONE: 1,
    TaskState.POSTPONED: 10,
    'overdue': 10,
}
