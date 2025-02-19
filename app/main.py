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

# GPIO 설정
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

class HardwareTest:
    def __init__(self):
        print("\n=== 하드웨어 테스트 시작 ===")
        
        # GPIO 핀 번호 설정
        self.MOTOR_FORWARD = 17
        self.MOTOR_BACKWARD = 18
        self.MOTOR_SPEED = 12
        self.ULTRASONIC_TRIGGER = 23
        self.ULTRASONIC_ECHO = 24
        self.WEIGHT_DOUT = 14
        self.WEIGHT_SCK = 15
        
        # GPIO 초기화
        try:
            # 모터 핀 설정
            GPIO.setup(self.MOTOR_FORWARD, GPIO.OUT)
            GPIO.setup(self.MOTOR_BACKWARD, GPIO.OUT)
            GPIO.setup(self.MOTOR_SPEED, GPIO.OUT)
            self.motor_pwm = GPIO.PWM(self.MOTOR_SPEED, 100)  # 100Hz PWM
            self.motor_pwm.start(0)
            print("모터 GPIO 초기화 완료")
            
            # 초음파 센서 핀 설정
            GPIO.setup(self.ULTRASONIC_TRIGGER, GPIO.OUT)
            GPIO.setup(self.ULTRASONIC_ECHO, GPIO.IN)
            print("초음파 센서 GPIO 초기화 완료")
            
            # 무게 센서 핀 설정
            GPIO.setup(self.WEIGHT_DOUT, GPIO.IN)
            GPIO.setup(self.WEIGHT_SCK, GPIO.OUT)
            print("무게 센서 GPIO 초기화 완료")
            
            self.system_running = True
            print("\n모든 GPIO 초기화 완료")
            
        except Exception as e:
            print(f"GPIO 초기화 오류: {str(e)}")
            GPIO.cleanup()
            sys.exit(1)
    
    def read_ultrasonic(self):
        """초음파 센서 거리 측정"""
        try:
            GPIO.output(self.ULTRASONIC_TRIGGER, False)
            time.sleep(0.2)  # 센서 안정화
            
            # 트리거 신호 전송
            GPIO.output(self.ULTRASONIC_TRIGGER, True)
            time.sleep(0.00001)  # 10μs
            GPIO.output(self.ULTRASONIC_TRIGGER, False)
            
            # 에코 신호 대기
            while GPIO.input(self.ULTRASONIC_ECHO) == 0:
                pulse_start = time.time()
            
            while GPIO.input(self.ULTRASONIC_ECHO) == 1:
                pulse_end = time.time()
            
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # cm 변환
            return round(distance, 1)
            
        except Exception as e:
            print(f"초음파 센서 오류: {str(e)}")
            return None
    
    def read_weight(self):
        """무게 센서 읽기 (HX711 프로토콜)"""
        try:
            # 여기에 실제 HX711 읽기 로직 구현
            # 지금은 테스트를 위해 임의의 값 반환
            return 150.0
        except Exception as e:
            print(f"무게 센서 오류: {str(e)}")
            return None
    
    def main_loop(self):
        """메인 테스트 루프"""
        print("\n=== GPIO 테스트 시작 ===")
        print("Ctrl+C로 종료할 수 있습니다.\n")
        
        try:
            while self.system_running:
                # 초음파 센서 읽기
                distance = self.read_ultrasonic()
                if distance is not None:
                    print(f"[초음파] 거리: {distance}cm")
                
                # 무게 센서 읽기
                weight = self.read_weight()
                if weight is not None:
                    print(f"[무게] 측정값: {weight}g")
                
                # 물체가 가까이 있으면 모터 작동
                if distance is not None and distance < 15:
                    print("\n물체 감지! 모터 작동...")
                    GPIO.output(self.MOTOR_FORWARD, GPIO.HIGH)
                    self.motor_pwm.ChangeDutyCycle(50)  # 50% 속도
                    time.sleep(1)
                    GPIO.output(self.MOTOR_FORWARD, GPIO.LOW)
                    self.motor_pwm.ChangeDutyCycle(0)
                    print("모터 정지\n")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n테스트를 종료합니다...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """GPIO 정리"""
        print("\nGPIO 정리 중...")
        self.motor_pwm.stop()
        GPIO.cleanup()
        print("정리 완료")

if __name__ == "__main__":
    test = HardwareTest()
    test.main_loop()