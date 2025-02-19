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
import RPi.GPIO as GPIO
import subprocess

# 한글 출력을 위한 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 버퍼링 없이 즉시 출력하도록 설정
print = lambda x: sys.stdout.write(str(x) + '\n')
sys.stdout.flush()

# GPIO 경고 메시지 무시
warnings.filterwarnings('ignore', category=RuntimeWarning)

# GPIO Mock 설정
import os
from gpiozero import Device
from gpiozero.pins.mock import MockFactory

# GPIO 모의(Mock) 핀 팩토리 설정
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

# 로그 디렉토리 생성
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# 기본 로거 설정
logger = logging.getLogger('pet_feeder')
logger.setLevel(logging.INFO)
logger.handlers = []  # 기존 핸들러 제거

# 파일 핸들러 설정
log_file = log_dir / 'pet_feeder.log'
file_handler = logging.FileHandler(log_file, encoding='utf-8')
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

class HardwareController:
    def __init__(self):
        try:
            # GPIO 설정
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # 핀 설정
            self.MOTOR_FORWARD = 17
            self.MOTOR_BACKWARD = 18
            self.MOTOR_SPEED = 12
            self.ULTRASONIC_TRIGGER = 23
            self.ULTRASONIC_ECHO = 24
            self.WEIGHT_DOUT = 14
            self.WEIGHT_SCK = 15
            
            # GPIO 초기화
            self._init_motor()
            self._init_ultrasonic()
            self._init_weight_sensor()
            
            # 이미지 저장 경로
            self.image_dir = Path("data/images")
            self.image_dir.mkdir(parents=True, exist_ok=True)
            
            print("하드웨어 초기화 완료")
            
        except Exception as e:
            print(f"하드웨어 초기화 실패: {str(e)}")
            if "Cannot determine SOC peripheral base address" in str(e):
                print("\n다음 명령어를 실행해보세요:")
                print("sudo chmod a+rw /dev/gpiomem")
                print("sudo systemctl start pigpiod")
            raise
        
    def _init_motor(self):
        GPIO.setup(self.MOTOR_FORWARD, GPIO.OUT)
        GPIO.setup(self.MOTOR_BACKWARD, GPIO.OUT)
        GPIO.setup(self.MOTOR_SPEED, GPIO.OUT)
        self.motor_pwm = GPIO.PWM(self.MOTOR_SPEED, 1000)
        self.motor_pwm.start(0)
        
    def _init_ultrasonic(self):
        GPIO.setup(self.ULTRASONIC_TRIGGER, GPIO.OUT)
        GPIO.setup(self.ULTRASONIC_ECHO, GPIO.IN)
        
    def _init_weight_sensor(self):
        GPIO.setup(self.WEIGHT_DOUT, GPIO.IN)
        GPIO.setup(self.WEIGHT_SCK, GPIO.OUT)
    
    def read_distance(self):
        GPIO.output(self.ULTRASONIC_TRIGGER, False)
        time.sleep(0.2)
        
        GPIO.output(self.ULTRASONIC_TRIGGER, True)
        time.sleep(0.00001)
        GPIO.output(self.ULTRASONIC_TRIGGER, False)
        
        while GPIO.input(self.ULTRASONIC_ECHO) == 0:
            pulse_start = time.time()
        
        while GPIO.input(self.ULTRASONIC_ECHO) == 1:
            pulse_end = time.time()
            
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        return round(distance, 2)
    
    def control_motor(self, speed, direction='forward'):
        if direction == 'forward':
            GPIO.output(self.MOTOR_FORWARD, GPIO.HIGH)
            GPIO.output(self.MOTOR_BACKWARD, GPIO.LOW)
        else:
            GPIO.output(self.MOTOR_FORWARD, GPIO.LOW)
            GPIO.output(self.MOTOR_BACKWARD, GPIO.HIGH)
            
        self.motor_pwm.ChangeDutyCycle(speed)
    
    def capture_image(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.image_dir / f"capture_{timestamp}.jpg"
        
        cmd = [
            'libcamera-still',
            '--width', '3280',
            '--height', '2464',
            '--output', str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return str(output_path)
        except subprocess.CalledProcessError as e:
            print(f"이미지 캡처 실패: {e}")
            return None
    
    def cleanup(self):
        self.motor_pwm.stop()
        GPIO.cleanup()
        print("하드웨어 정리 완료")

def main():
    controller = None
    try:
        controller = HardwareController()
        print("\n=== 하드웨어 테스트 시작 ===")
        
        while True:
            # 거리 측정
            distance = controller.read_distance()
            print(f"\n거리: {distance}cm")
            
            # 물체가 가까이 있으면
            if distance < 15:
                print("물체 감지!")
                
                # 사진 촬영
                image_path = controller.capture_image()
                if image_path:
                    print(f"이미지 저장: {image_path}")
                
                # 모터 작동
                # print("모터 작동...")
                # controller.control_motor(50, 'forward')
                # time.sleep(2)
                # controller.control_motor(0)
                # print("모터 정지")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n프로그램 종료")
    finally:
        if controller:
            controller.cleanup()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("이 프로그램은 root 권한으로 실행해야 합니다.")
        print("다음 명령어로 실행하세요:")
        print("sudo python3 -m venv venv")
        print("source venv/bin/activate")
        print("sudo python3 main.py")
        sys.exit(1)
    main()