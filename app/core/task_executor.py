import random
import time
import json
from datetime import datetime
from hardware.weight_sensor import WeightSensor

class TaskExecutor:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.weight_sensor = WeightSensor()
        self.tasks = {
            "ultrasonic": self.ultrasonic_task,
            "camera": self.camera_task,
            "feeding": self.feeding_task,
            "weight": self.weight_task
        }
        self.feeding_schedule_path = "schedule/feeding_schedule.json"
        self.feeding_history_path = "schedule/feeding_history.json"
        self.feeding_window_minutes = 5  # 급여 가능 시간 윈도우 (분)
        
    def load_feeding_schedule(self):
        """급여 일정 로드"""
        try:
            with open(self.feeding_schedule_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"급여 일정 로드 실패: {str(e)}")
            return None

    def load_feeding_history(self):
        """급여 이력 로드"""
        try:
            with open(self.feeding_history_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"feedings": []}
        except Exception as e:
            print(f"급여 이력 로드 실패: {str(e)}")
            return {"feedings": []}

    def save_feeding_history(self, feeding_data):
        """급여 이력 저장"""
        try:
            history = self.load_feeding_history()
            history["feedings"].append(feeding_data)
            with open(self.feeding_history_path, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"급여 이력 저장 실패: {str(e)}")

    def is_feeding_time(self, schedule_time):
        """급여 시간 범위 내인지 확인"""
        current_time = datetime.now()
        schedule_hour, schedule_minute = map(int, schedule_time.split(':'))
        
        # 현재 시간이 예정된 시간보다 이전이면서 feeding_window_minutes 내에 있는지 확인
        if current_time.hour == schedule_hour:
            # 같은 시간대일 경우
            if schedule_minute - self.feeding_window_minutes <= current_time.minute < schedule_minute:
                return False  # 아직 급여 시간이 되지 않음
            elif schedule_minute <= current_time.minute <= schedule_minute + self.feeding_window_minutes:
                return True  # 급여 가능 시간
        
        return False  # 그 외의 경우는 급여 시간이 아님

    def is_already_fed(self, schedule_time):
        """해당 시간대 급여 여부 확인"""
        history = self.load_feeding_history()
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        for feeding in history["feedings"]:
            if (feeding["date"] == current_date and 
                feeding["scheduled_time"] == schedule_time):
                return True
        return False

    def get_current_feeding_amount(self):
        """현재 시간에 맞는 급여량 확인"""
        schedule = self.load_feeding_schedule()
        if not schedule:
            return None

        for feeding in schedule["feedings"]:
            schedule_time = feeding["time"]
            
            # 이미 급여했는지 확인
            if self.is_already_fed(schedule_time):
                continue
                
            # 급여 시간 범위 내인지 확인
            if self.is_feeding_time(schedule_time):
                return {
                    "amount": feeding["amount"],
                    "scheduled_time": schedule_time
                }
        
        return None

    def execute_task(self, task_id):
        if task_id in self.tasks:
            return self.tasks[task_id]()
        return {"status": "error", "message": f"Task {task_id} not found"}

    def feeding_task(self):
        """급여 작업 실행"""
        try:
            feeding_info = self.get_current_feeding_amount()
            
            if feeding_info is None:
                return {
                    "status": "error", 
                    "message": "현재 시간에 해당하는 급여 일정이 없거나, 이미 급여를 완료했습니다."
                }

            amount = feeding_info["amount"]
            scheduled_time = feeding_info["scheduled_time"]
            
            print(f"급여 시작... {amount}g 급여 중")
            # 여기에 실제 급여 장치 제어 코드 추가
            time.sleep(2)  # 급여 작업 시뮬레이션

            # 급여 후 무게 확인
            weight_result = self.weight_task()
            
            # 급여 이력 저장
            feeding_data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "scheduled_time": scheduled_time,
                "actual_time": datetime.now().strftime("%H:%M:%S"),
                "amount": amount,
                "weight_after": weight_result["data"] if weight_result["status"] == "success" else None
            }
            self.save_feeding_history(feeding_data)

            if weight_result["status"] == "success":
                return {
                    "status": "success",
                    "data": {
                        "amount_fed": amount,
                        "weight_after": weight_result["data"],
                        "scheduled_time": scheduled_time
                    }
                }
            else:
                return {
                    "status": "partial_success",
                    "data": {
                        "amount_fed": amount,
                        "scheduled_time": scheduled_time
                    },
                    "message": "급여 완료됨, 무게 확인 실패"
                }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def weight_task(self):
        """무게 측정 작업"""
        try:
            weight = self.weight_sensor.get_weight()
            if weight is not None:
                print(f"현재 무게: {weight:.1f}g")
                return {"status": "success", "data": weight}
            else:
                return {"status": "error", "message": "무게 측정 실패"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def ultrasonic_task(self):
        try:
            distance = random.uniform(5, 30)
            print(f"Ultrasonic reading: {distance:.1f}cm")
            time.sleep(0.5)
            return {"status": "success", "data": distance}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def camera_task(self):
        try:
            print("Taking a photo...")
            time.sleep(1)
            return {"status": "success", "data": "image_captured"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def cleanup(self):
        """리소스 정리"""
        self.weight_sensor.cleanup()