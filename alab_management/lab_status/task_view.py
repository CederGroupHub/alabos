class TaskView:
    """
    Task view support operations related to current task queue.
    """
    def query_task(self, task_id):
        ...

    def delete_task(self, task_id):
        ...

    def update_task(self, task_id, updated):
        ...

    def get_next_task(self, task_id):
        ...

    def get_prev_task(self, task_id):
        ...
