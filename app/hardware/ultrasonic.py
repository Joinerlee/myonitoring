from gpiozero import DistanceSensor
import time
from typing import Optional
from statistics import mean

class UltrasonicSensor:
    """HC-SR04 초음파 센서를 위한 클래스
    
    Attributes:
        echo_pin (int): Echo 핀 번호
        trigger_pin (int): Trigger 핀 번호
        max_distance (float): 최대 측정 거리 (미터 단위)
        threshold_distance (float): 감지 기준 거리 (센티미터 단위)
        min_distance (float): 최소 안전 거리 (센티미터 단위)
    """
    
    def __init__(self, 
                 echo_pin: int = 18, 
                 trigger_pin: int = 17, 
                 max_distance: float = 0.3,  # 30cm로 제한
                 threshold_distance: float = 25,  # 25cm로 설정
                 min_distance: float = 2):  # 최소 2cm
        """초음파 센서 초기화
        
        Args:
            echo_pin (int): Echo 핀 번호 (기본값: 18)
            trigger_pin (int): Trigger 핀 번호 (기본값: 17)
            max_distance (float): 최대 측정 거리 (미터 단위, 기본값: 0.3m = 30cm)
            threshold_distance (float): 감지 기준 거리 (센티미터 단위, 기본값: 25cm)
            min_distance (float): 최소 안전 거리 (센티미터 단위, 기본값: 2cm)
        """
        try:
            self.sensor = DistanceSensor(
                echo=echo_pin,
                trigger=trigger_pin,
                max_distance=max_distance,
                partial=True  # partial=True로 설정하여 측정 시간 제한
            )
            self.threshold_distance = threshold_distance
            self.min_distance = min_distance
            self.max_distance_cm = max_distance * 100
            self._is_initialized = True
            
            # 센서 워밍업
            self._warmup()
            
        except Exception as e:
            print(f"초음파 센서 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def _warmup(self, warmup_time: float = 1.0):
        """센서 워밍업
        
        Args:
            warmup_time (float): 워밍업 시간 (초)
        """
        time.sleep(warmup_time)
    
    def get_distance(self) -> Optional[float]:
        """현재 거리를 측정합니다.
        
        Returns:
            float: 측정된 거리 (센티미터 단위)
            None: 측정 실패시
        """
        if not self._is_initialized:
            return None
            
        try:
            # 거리 측정 (미터 단위를 센티미터로 변환)
            distance = self.sensor.distance * 100
            
            # 최소 거리보다 가까우면 None 반환
            if distance < self.min_distance:
                return None
                
            # 최대 거리보다 멀면 최대 거리 반환
            if distance > self.max_distance_cm:
                return self.max_distance_cm
                
            return distance
            
        except Exception as e:
            print(f"거리 측정 실패: {str(e)}")
            return None
    
    def is_object_detected(self) -> bool:
        """설정된 임계값 거리 이내에 물체가 있는지 확인합니다.
        
        Returns:
            bool: 물체 감지 여부
        """
        distance = self.get_distance()
        if distance is None:
            return False
        return self.min_distance <= distance <= self.threshold_distance
    
    def get_average_distance(self, samples: int = 3, interval: float = 0.1) -> Optional[float]:
        """여러 번 측정하여 평균 거리를 계산합니다.
        
        Args:
            samples (int): 측정 횟수 (기본값: 3)
            interval (float): 측정 간격 (초 단위, 기본값: 0.1초)
            
        Returns:
            float: 평균 거리 (센티미터 단위)
            None: 측정 실패시
        """
        if not self._is_initialized:
            return None
            
        distances = []
        for _ in range(samples):
            distance = self.get_distance()
            if distance is not None and self.min_distance <= distance <= self.max_distance_cm:
                distances.append(distance)
            time.sleep(interval)
        
        return mean(distances) if distances else None
    
    def cleanup(self):
        """센서 리소스를 정리합니다."""
        if self._is_initialized:
            self.sensor.close()
            self._is_initialized = False