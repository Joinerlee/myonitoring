# app/hardware/motor.py

from gpiozero import Motor, PWMOutputDevice, Device
from time import sleep, time
from typing import Optional

class PIDController:
    def __init__(self, kp, ki, kd, setpoint, max_output=0.6):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.max_output = max_output
        self.previous_error = 0
        self.integral = 0
        self.last_time = time()
        self.last_value = None

    def compute(self, current_value):
        if abs(current_value - self.setpoint) < 0.1:
            return None

        current_time = time()
        dt = current_time - self.last_time
        error = self.setpoint - current_value

        if self.last_value is not None:
            value_change = abs(current_value - self.last_value)
            if value_change > 5:
                self.integral = 0
                print(f"급격한 변화 감지! ({value_change:.1f}) - 제어 재조정")

        self.integral = max(min(self.integral + error * dt, 5), -5)
        derivative = (error - self.previous_error) / dt if dt > 0 else 0

        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)

        error_magnitude = abs(error)
        if error_magnitude > 10:
            speed_limit = self.max_output * 0.8
        elif error_magnitude > 5:
            speed_limit = self.max_output * 0.6
        else:
            speed_limit = self.max_output * 0.4

        self.previous_error = error
        self.last_time = current_time
        self.last_value = current_value

        return max(0, min(speed_limit, output))

class MotorController:
    def __init__(self,
                 forward_pin: int = 17,  # GPIO17
                 backward_pin: int = 18,  # GPIO18
                 speed_pin: int = 12,     # GPIO12
                 default_speed: float = 0.7
                 ):
        try:
            print("[motor] 모터 컨트롤러 초기화 시작...")
            print(f"[motor] 설정: forward={forward_pin}, backward={backward_pin}, speed={speed_pin}")
            print(f"[motor] 기본 속도: {default_speed}")
            
            # 이전 GPIO 설정 초기화
            try:
                if Device.pin_factory:
                    Device.pin_factory.reset()
            except:
                pass
            
            # 모터 및 속도 제어 초기화
            self.motor = Motor(forward=forward_pin, backward=backward_pin)
            self.speed = PWMOutputDevice(speed_pin)
            self.default_speed = default_speed
            self._is_running = False
            self._is_initialized = True
            
            # PID 컨트롤러 초기화
            self.pid = PIDController(
                kp=0.05,   # 비례 게인
                ki=0.003,  # 적분 게인
                kd=0.02,   # 미분 게인
                setpoint=20,
                max_output=0.6
            )
            
            print("[motor] 초기화 완료")
            
        except Exception as e:
            print(f"[motor] 초기화 실패: {str(e)}")
            self._is_initialized = False

    def start_feeding(self, target_weight: float = None) -> bool:
        if not self._is_initialized:
            print("[motor] 모터가 초기화되지 않았습니다")
            return False
            
        try:
            print(f"[motor] 급여 시작 (목표 무게: {target_weight}g)")
            self.motor.forward()
            self._is_running = True
            
            # 초기 속도 설정 (40%로 시작)
            self.speed.value = self.default_speed * 0.4
            return True
            
        except Exception as e:
            print(f"[motor] 모터 구동 실패: {str(e)}")
            return False

    def stop_feeding(self) -> bool:
        if not self._is_initialized:
            print("[motor] 모터가 초기화되지 않았습니다")
            return False
            
        try:
            print("[motor] 급여 정지")
            self.motor.stop()
            self.speed.off()
            self._is_running = False
            return True
        except Exception as e:
            print(f"[motor] 모터 정지 실패: {str(e)}")
            return False

    def adjust_speed(self, current_weight: float, target_weight: float) -> None:
        if not self._is_running:
            return
            
        try:
            control_value = self.pid.compute(current_weight)
            if control_value is None:
                self.stop_feeding()
                return
                
            self.speed.value = control_value
            print(f"[motor] 현재 무게: {current_weight:.1f}g, 속도: {control_value*100:.1f}%")
            
        except Exception as e:
            print(f"[motor] 속도 조절 실패: {str(e)}")

    def cleanup(self):
        print("[motor] 리소스 정리")
        if self._is_initialized:
            self.stop_feeding()
            self.speed.close()
            self._is_initialized = False
                                    