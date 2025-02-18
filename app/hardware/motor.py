# app/hardware/motor.py

from gpiozero import Motor
from time import sleep
from typing import Optional

class MotorController:
    """DC 모터 제어 클래스 (L298N 모터 드라이버 사용)"""
    
    def __init__(self,
                 forward_pin: int = 23,  # GPIO23
                 backward_pin: int = 22,  # GPIO22
                 default_speed: float = 0.7
                 ):
        """
        Args:
            forward_pin (int): 정방향 회전 제어 핀
            backward_pin (int): 역방향 회전 제어 핀
            default_speed (float): 기본 모터 속도 (0~1 사이값)
        """
        try:
            self.motor = Motor(forward=forward_pin, backward=backward_pin)
            self.default_speed = default_speed
            self._is_running = False
            self._is_initialized = True
        except Exception as e:
            print(f"모터 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def start_feeding(self, speed: Optional[float] = None) -> bool:
        """모터 정방향 회전 시작[1]"""
        if not self._is_initialized:
            return False
            
        try:
            self.motor.forward(speed or self.default_speed)
            self._is_running = True
            return True
        except Exception as e:
            print(f"모터 구동 실패: {str(e)}")
            return False
    
    def stop_feeding(self) -> bool:
        """모터 정지[2]"""
        if not self._is_initialized:
            return False
            
        try:
            self.motor.stop()
            self._is_running = False
            return True
        except Exception as e:
            print(f"모터 정지 실패: {str(e)}")
            return False
    
    def cleanup(self):
        """모터 리소스 정리"""
        if self._is_initialized:
            self.stop_feeding()
            self._is_initialized = False
                                    