# app/core/system_controller.py

from hardware.camera import CameraIMX219
from hardware.ultrasonic import UltrasonicSensor
from hardware.weight_sensor import WeightSensor
from hardware.motor import MotorController
from models.eye_detection import EyeDetectionModel
from typing import Dict, Optional
import time
import threading

class SystemController:
    """통합 시스템 제어 클래스"""
    
    def __init__(self):
        # 하드웨어 초기화
        self.camera = CameraIMX219()
        self.ultrasonic = UltrasonicSensor()
        self.weight_sensor = WeightSensor()
        self.motor = MotorController()
        
        # AI 모델 초기화
        self.eye_detector = EyeDetectionModel()
        
        # 시스템 상태
        self._running = False
        self._is_initialized = all([
            self.camera._is_initialized,
            self.ultrasonic._is_initialized,
            self.weight_sensor._is_initialized,
            self.motor._is_initialized
        ])
    
    def start_monitoring(self):
        """시스템 모니터링 시작[1]"""
        if not self._is_initialized:
            return False
            
        self._running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
        return True
    
    def _monitor_loop(self):
        """메인 모니터링 루프[2]"""
        while self._running:
            try:
                # 초음파 센서로 고양이 감지
                if self.ultrasonic.check_obstacle():
                    # 카메라 촬영 시작
                    images = self.camera.start_capture()
                    if images:
                        # AI 분석 수행
                        results = self.eye_detector.batch_process(images)
                        self._handle_detection_results(results)
                
                time.sleep(0.1)  # 100ms 간격
                
            except Exception as e:
                print(f"모니터링 오류: {str(e)}")
    
    def _handle_detection_results(self, results: list):
        """AI 분석 결과 처리[3]"""
        if not results:
            return
            
        # 질병 확률이 가장 높은 결과 선택
        best_result = max(results, key=lambda x: x['disease_probability'])
        if best_result['disease_probability'] >= 0.5:
            # Firebase 저장 로직 구현 필요
            pass
