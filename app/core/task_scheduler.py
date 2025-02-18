class RTOSScheduler:
    def __init__(self):
        self.tasks = {}
        self.task_queue = []
        self.task_statuses = {}
        
    def add_task(self, task_id, priority=1):
        self.tasks[task_id] = {"priority": priority}
        self.task_queue.append(task_id)
        self.task_statuses[task_id] = "pending"
        
    def get_next_task(self):
        if not self.task_queue:
            for task_id in self.tasks.keys():
                self.task_queue.append(task_id)
        return self.task_queue.pop(0) if self.task_queue else None
    
    def set_task_status(self, task_id, status):
        self.task_statuses[task_id] = status
        if status == "ready":
            self.task_queue.append(task_id)