class RTOSScheduler:
    def __init__(self):
        self.tasks = {
            'ultrasonic': {'priority': 1, 'interval': 0.1},  # 100ms
            'weight': {'priority': 1, 'interval': 0.1},      # 100ms
            'schedule': {'priority': 2, 'interval': 1.0},    # 1s
            'error': {'priority': 3, 'interval': 5.0},       # 5s
            'camera': {'priority': 2, 'interval': 0.5}       # 500ms (when active)
        }
        self.task_queue = []
        self.task_statuses = {}
        self.last_run_time = {task: 0 for task in self.tasks}
        
    def should_run_task(self, task_id, current_time):
        if task_id not in self.last_run_time:
            return True
        return (current_time - self.last_run_time[task_id]) >= self.tasks[task_id]['interval']
    
    def update_task_time(self, task_id, current_time):
        self.last_run_time[task_id] = current_time
        
    def get_next_task(self, current_time):
        eligible_tasks = [
            task for task in self.tasks 
            if self.should_run_task(task, current_time)
        ]
        if not eligible_tasks:
            return None
            
        return min(eligible_tasks, key=lambda x: self.tasks[x]['priority'])
    
    def set_task_status(self, task_id, status):
        self.task_statuses[task_id] = status
        if status == "ready":
            self.task_queue.append(task_id)