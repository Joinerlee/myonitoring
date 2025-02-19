# app/hardware/ultrasonic.py

from gpiozero import DigitalOutputDevice, DigitalInputDevice
import time
from typing import Optional

class UltrasonicSensor:
    """HC-SR04 초음파 센서 클래스"""
    
    def __init__(self, echo_pin=24, trigger_pin=23):
        """
        Args:
            echo_pin (int): Echo 핀 번호 (기본값: 24)
            trigger_pin (int): Trigger 핀 번호 (기본값: 23)
        """
        try:
            print("[ultrasonic] 초음파 센서 초기화 시작...")
            print(f"[ultrasonic] 설정: echo={echo_pin}, trigger={trigger_pin}")
            
            self.echo = DigitalInputDevice(echo_pin)
            self.trigger = DigitalOutputDevice(trigger_pin)
            self._is_initialized = True
            
            print("[ultrasonic] 초기화 완료")
            
        except Exception as e:
            print(f"[ultrasonic] 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def get_distance(self) -> Optional[float]:
        """거리 측정 (센티미터 단위로 반환)"""
        if not self._is_initialized:
            print("[ultrasonic] 센서가 초기화되지 않았습니다")
            return None
            
        try:
            # 트리거 신호 전송
            self.trigger.on()
            time.sleep(0.00001)  # 10μs
            self.trigger.off()
            
            # 에코 신호 대기
            pulse_start = time.time()
            while not self.echo.value:
                pulse_start = time.time()
                if time.time() - pulse_start > 0.1:  # 타임아웃
                    return None
            
            # 에코 신호 수신
            pulse_end = time.time()
            while self.echo.value:
                pulse_end = time.time()
                if time.time() - pulse_start > 0.1:  # 타임아웃
                    return None
            
            # 거리 계산
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # (340m/s * 100cm/m) / 2
            
            return round(distance, 2)
            
        except Exception as e:
            print(f"[ultrasonic] 거리 측정 실패: {str(e)}")
            return None
    
    def check_obstacle(self) -> bool:
        """물체가 임계값(15cm)보다 가까이 있는지 확인[4]"""
        if not self._is_initialized:
            print("[ultrasonic] 센서가 초기화되지 않았습니다")
            return False
        distance = self.get_distance()
        if distance is None:
            return False
        is_detected = distance <= 15.0
        if is_detected:
            print(f"[ultrasonic] 물체 감지! (거리: {distance:.1f}cm)")
        return is_detected
    
    def cleanup(self):
        """센서 리소스 정리"""
        print("[ultrasonic] 리소스 정리")
        if hasattr(self, 'trigger'):
            self.trigger.close()
        if hasattr(self, 'echo'):
            self.echo.close()

    def get_pulse_duration(self) -> Optional[float]:
        """초음파 센서의 펄스 지속 시간 반환"""
        if not self._is_initialized:
            return None
        
        try:
            self.trigger.on()
            time.sleep(0.00001)  # 10μs
            self.trigger.off()
            
            pulse_start = time.time()
            while not self.echo.value:
                pulse_start = time.time()
                if time.time() - pulse_start > 0.1:  # 타임아웃
                    return None
            
            pulse_end = time.time()
            while self.echo.value:
                pulse_end = time.time()
                if time.time() - pulse_start > 0.1:  # 타임아웃
                    return None
            
            return pulse_end - pulse_start
            
        except Exception as e:
            print(f"[ultrasonic] 펄스 측정 실패: {str(e)}")
            return None
