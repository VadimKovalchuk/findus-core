from task.models import NetworkTask, SystemTask, TaskState


class TaskType:
    Network = NetworkTask.__name__
    System = SystemTask.__name__
    ALL = (Network, System)


TASK_PROCESSING_QUOTAS = {
    TaskType.System: {
        TaskState.CREATED: 1,
        TaskState.PROCESSED: 2,
        TaskState.DONE: 1,
        TaskState.POSTPONED: 10
    },
    TaskType.Network: {
        TaskState.CREATED: 2,
        TaskState.PROCESSED: 4,
        TaskState.DONE: 1,
        TaskState.POSTPONED: 100
    }
}
