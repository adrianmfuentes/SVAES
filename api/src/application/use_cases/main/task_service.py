from application.ports.input.i_task_service import ITaskService
from application.ports.output.i_task_queue import ITaskQueue

class TaskService(ITaskService):
    def __init__(self, task_queue: ITaskQueue) -> None:
        self._task_queue = task_queue

    async def get_task_status(self, task_id: str):
        return await self._task_queue.get_task_status(task_id)