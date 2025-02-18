from core.task_scheduler import RTOSScheduler
from core.task_executor import TaskExecutor
from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime

class MainApplication:
    def __init__(self):
        self.scheduler = RTOSScheduler()
        self.executor = TaskExecutor(self.scheduler)
        self.background_scheduler = BackgroundScheduler()
        
        # 무게 관련 변수
        self.last_saved_weight = None
        self.last_stable_weight = None
        self.change_start_time = None
        self.change_start_weight = None  # 변화 시작시 무게 저장
        self.weight_data = []
        self.data_log_file = "weight_log.json"
        self.tare_value = 0  # 현재 영점값
        self.stable_count = 0  # 안정화 카운터

        # 초기 태스크 설정
        self.scheduler.add_task("weight", priority=1)
        self.scheduler.add_task("ultrasonic", priority=2)
        self.scheduler.add_task("camera", priority=3)
        self.scheduler.add_task("feeding", priority=4)
    
    def check_feeding_schedule(self):
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Checking feeding schedule...")
            self.scheduler.set_task_status("feeding", "ready")
        except Exception as e:
            print(f"Error in feeding schedule check: {e}")
    
    def setup_background_tasks(self):
        self.background_scheduler.add_job(
            self.check_feeding_schedule,
            'interval',
            minutes=3,
            id='feeding_check'
        )
        self.background_scheduler.start()
    
    def cleanup(self):
        self.background_scheduler.shutdown()
        self.executor.cleanup()
    
    def save_weight_data(self):
        """무게 데이터를 JSON 파일로 저장"""
        import json
        try:
            with open(self.data_log_file, 'w') as f:
                json.dump(self.weight_data, f, indent=4)
            print("무게 데이터 저장 성공")
            return True
        except Exception as e:
            print(f"무게 데이터 저장 실패: {str(e)}")
            return False

    def handle_weight_change(self, weight):
        """무게 변화 감지 및 데이터 저장 로직"""
        actual_weight = round(weight - self.tare_value, 1)  # 소수점 첫째자리까지만 표시
        print(f"Current weight: {actual_weight}g")
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if self.last_saved_weight is not None:
            weight_change = abs(actual_weight - self.last_saved_weight)

            if weight_change >= 5:  # 5g 이상의 변화 감지
                self.stable_count = 0  # 안정화 카운터 리셋
                
                if self.change_start_time is None:
                    # 변화 시작 시점 기록
                    self.change_start_time = current_time
                    self.change_start_weight = self.last_saved_weight
                    print(f"Weight change started at {current_time}")
            else:  # 무게 변화가 5g 미만일 때
                if self.change_start_time is not None:
                    self.stable_count += 1
                    
                    # 3회 연속으로 안정적인 무게가 감지되면 변화 구간 종료로 간주
                    if self.stable_count >= 3:
                        # 변화 구간 데이터 저장
                        total_change = abs(actual_weight - self.change_start_weight)
                        self.weight_data.append({
                            'start_time': self.change_start_time,
                            'end_time': current_time,
                            'start_weight': self.change_start_weight,
                            'end_weight': actual_weight,
                            'total_change': total_change
                        })
                        self.save_weight_data()
                        print(f"Weight change ended at {current_time}")
                        print(f"Total change: {total_change}g")
                        
                        # 변화 관련 변수 초기화
                        self.change_start_time = None
                        self.change_start_weight = None
                        self.stable_count = 0
            
            self.last_saved_weight = actual_weight
        else:
            self.last_saved_weight = actual_weight
        
        return actual_weight

    def run(self):
        try:
            print("Starting application...")
            self.setup_background_tasks()
            
            while True:
                try:
                    next_task = self.scheduler.get_next_task()
                    if next_task:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"\n[{current_time}] Executing task: {next_task}")
                        result = self.executor.execute_task(next_task)
                        
                        if result and isinstance(result, dict):
                            if result["status"] == "success":
                                if next_task == "ultrasonic" and isinstance(result["data"], (int, float)):
                                    if result["data"] <= 15:
                                        print("Motion detected, triggering camera task")
                                        self.scheduler.set_task_status("camera", "ready")
                                elif next_task == "weight" and isinstance(result["data"], (int, float)):
                                    weight_value = result["data"]
                                    actual_weight = self.handle_weight_change(weight_value)

                                    if actual_weight < 100:
                                        print("Low food weight detected, triggering feeding task")
                                        self.scheduler.set_task_status("feeding", "ready")
                                
                                print(f"Task {next_task} completed successfully")
                                self.scheduler.add_task(next_task)
                            else:
                                print(f"Task {next_task} failed: {result.get('message', 'Unknown error')}")
                    
                    time.sleep(0.1)
                    
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    self.cleanup()
                    break
                except Exception as e:
                    print(f"Error in main loop: {e}")
                    time.sleep(1)
        finally:
            self.cleanup()

if __name__ == "__main__":
    app = MainApplication()
    app.run()