# app/hardware/ultrasonic.py

from gpiozero import DistanceSensor
from time import sleep
from typing import Optional

class UltrasonicSensor:
    """HC-SR04 초음파 센서 클래스"""
    
    def __init__(self, 
                 echo_pin: int = 24, 
                 trigger_pin: int = 23, 
                 max_distance: float = 1.0,      # 최대 1m
                 threshold_distance: float = 0.15  # 15cm = 0.15m
                 ):
        """
        Args:
            echo_pin (int): Echo 핀 번호 (기본값: 24)
            trigger_pin (int): Trigger 핀 번호 (기본값: 23)
            max_distance (float): 최대 측정 거리 (미터 단위, 기본값: 1m)
            threshold_distance (float): 감지 임계값 (미터 단위, 기본값: 0.15m)
        """
        try:
            self.sensor = DistanceSensor(
                echo=echo_pin,
                trigger=trigger_pin,
                max_distance=max_distance,
                threshold_distance=threshold_distance
            )
            self._is_initialized = True
            self.threshold_distance = threshold_distance
        except Exception as e:
            print(f"초음파 센서 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def get_distance(self) -> Optional[float]:
        """거리 측정 (센티미터 단위로 반환)"""
        if not self._is_initialized:
            return None
            
        try:
            # 미터를 센티미터로 변환[1]
            return self.sensor.distance * 100
        except Exception as e:
            print(f"거리 측정 실패: {str(e)}")
            return None
    
    def check_obstacle(self) -> bool:
        """물체가 임계값(15cm)보다 가까이 있는지 확인[4]"""
        if not self._is_initialized:
            return False
        distance = self.get_distance()
        if distance is None:
            return False
        return distance <= (self.threshold_distance * 100)
    
    def cleanup(self):
        """센서 리소스 정리"""
        if self._is_initialized:
            self.sensor.close()
            self._is_initialized = False
