# app/main.py

import asyncio
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional, Dict, Any
import os
import sys
import locale
import io
import warnings

# 한글 출력을 위한 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 버퍼링 없이 즉시 출력하도록 설정
print = lambda x: sys.stdout.write(str(x) + '\n')
sys.stdout.flush()

# GPIO 경고 메시지 무시
warnings.filterwarnings('ignore', category=RuntimeWarning)

# GPIO 설정
import os
from gpiozero import Motor, PWMOutputDevice, Device
from gpiozero.pins.mock import MockFactory

# GPIO 모의(Mock) 핀 팩토리 설정
os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'
Device.pin_factory = MockFactory()

# 기존 GPIO 설정 초기화
try:
    Device.pin_factory.reset()
except:
    pass

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import logging

from hardware.camera import CameraIMX219
from hardware.motor import MotorController
from hardware.ultrasonic import UltrasonicSensor
from hardware.weight_sensor import WeightSensor
from utils.error_handler import ErrorHandler
from utils.file_manager import FileManager
from core.task_scheduler import RTOSScheduler

# 모든 로거의 핸들러 제거
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# uvicorn과 fastapi 로거 레벨 설정
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)

# 기본 로거 설정
logger = logging.getLogger('pet_feeder')
logger.setLevel(logging.INFO)
logger.handlers = []  # 기존 핸들러 제거

# 파일 핸들러 설정
file_handler = logging.FileHandler('logs/pet_feeder.log', encoding='utf-8')
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                 datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# 콘솔 출력은 print 문 사용
def log_info(msg: str):
    """로그 출력 및 저장"""
    print(msg)
    logger.info(msg)

def log_error(msg: str):
    """에러 로그 출력 및 저장"""
    print(f"[오류] {msg}")
    logger.error(msg)

class HardwareTest:
    def __init__(self):
        print("\n=== 하드웨어 테스트 시작 ===")
        
        # 하드웨어 초기화
        try:
            # 모터 초기화 (MotorController 사용)
            self.motor = MotorController(
                forward_pin=17, 
                backward_pin=18,
                speed_pin=12
            )
            print("모터 초기화 완료")
            
            # 초음파 센서 초기화
            self.ultrasonic = UltrasonicSensor(
                echo_pin=24,
                trigger_pin=23
            )
            print("초음파 센서 초기화 완료")
            
            # 무게 센서 초기화
            self.weight_sensor = WeightSensor(
                dout_pin=14,
                sck_pin=15
            )
            print("무게 센서 초기화 완료")
            
            # 카메라 초기화
            self.camera = CameraIMX219()
            print("카메라 초기화 완료")
            
            # 이미지 저장 경로 생성
            self.image_dir = Path("data/images")
            self.image_dir.mkdir(parents=True, exist_ok=True)
            
            # RTOS 스케줄러 초기화
            self.scheduler = RTOSScheduler()
            self.system_running = True
            
            print("\n모든 하드웨어 초기화 완료")
            
        except Exception as e:
            print(f"초기화 오류: {str(e)}")
            sys.exit(1)
    
    def run_motor(self, weight):
        """무게에 따른 모터 제어"""
        try:
            if weight < 100:  # 100g 미만이면 빠르게
                speed_value = 0.8
            elif weight < 200:  # 200g 미만이면 중간 속도
                speed_value = 0.5
            else:  # 그 이상이면 천천히
                speed_value = 0.3
            
            print(f"\n모터 구동 (무게: {weight:.1f}g, 속도: {speed_value*100:.0f}%)")
            self.motor.start_feeding()
            self.motor.set_speed(speed_value)
            time.sleep(2)  # 2초간 구동
            self.motor.stop_feeding()
            print("모터 정지")
            
        except Exception as e:
            print(f"모터 제어 오류: {str(e)}")
            self.motor.stop_feeding()
    
    def capture_images(self):
        """5장 연속 촬영"""
        try:
            print("\n=== 카메라 테스트 시작 ===")
            for i in range(5):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result = self.camera.capture()
                if result['status'] == 'success':
                    image_path = self.image_dir / f"test_{timestamp}.jpg"
                    print(f"이미지 저장: {image_path}")
                time.sleep(1)  # 1초 간격
            print("카메라 테스트 완료\n")
        except Exception as e:
            print(f"카메라 오류: {str(e)}")
    
    def main_loop(self):
        """메인 테스트 루프"""
        image_count = 0
        last_motor_time = 0
        last_print_time = 0
        
        try:
            print("\n=== 센서 테스트 시작 ===")
            while self.system_running:
                current_time = time.time()
                
                # 0.5초 간격으로 센서값 출력
                if current_time - last_print_time >= 0.5:  # 500ms 간격
                    print("\n현재 센서 상태:")
                    
                    # 초음파 센서 읽기
                    distance = self.ultrasonic.get_distance()
                    pulse_duration = self.ultrasonic.get_pulse_duration()
                    if distance is not None:
                        print(f"[초음파] 거리: {distance:.1f}cm (RAW: {pulse_duration:.6f}s)")
                    
                    # 무게 센서 읽기
                    raw_value = self.weight_sensor.read()
                    weight = self.weight_sensor.get_weight()
                    if weight is not None:
                        print(f"[무게] 측정값: {weight:.1f}g (RAW: {raw_value})")
                    
                    print("-" * 40)  # 구분선
                    sys.stdout.flush()
                    last_print_time = current_time
                
                # 물체 감지시 카메라 촬영 (5장만)
                if (distance is not None and 
                    distance < 15 and 
                    image_count < 5 and 
                    current_time - last_print_time >= 1):  # 최소 1초 간격
                    self.capture_images()
                    image_count = 5
                
                # 무게 변화에 따른 모터 제어 (5초 간격)
                if (weight is not None and 
                    current_time - last_motor_time > 5):  # 5초로 늘림
                    self.run_motor(weight)
                    last_motor_time = current_time
                
                time.sleep(0.1)  # 기본 루프 간격
                
        except KeyboardInterrupt:
            print("\n테스트를 종료합니다...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """하드웨어 정리"""
        print("\n하드웨어 정리 중...")
        self.motor.cleanup()
        self.ultrasonic.cleanup()
        self.weight_sensor.cleanup()
        print("정리 완료")

if __name__ == "__main__":
    test = HardwareTest()
    test.main_loop()