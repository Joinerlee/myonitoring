# app/main.py

import asyncio
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional, Dict, Any

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from hardware.camera import CameraIMX219
from hardware.motor import MotorController
from hardware.ultrasonic import UltrasonicSensor
from hardware.weight_sensor import WeightSensor
from utils.error_handler import ErrorHandler
from utils.file_manager import FileManager
from core.task_scheduler import RTOSScheduler

class PetFeeder:
    def __init__(self):
        # 시스템 설정 로드
        self.config = self.load_config()
        
        # 로거 설정
        self.setup_logger()
        
        # 파일 관리자 초기화
        self.file_manager = FileManager()
        self.error_handler = ErrorHandler()
        
        # 하드웨어 초기화
        self.init_hardware()
        
        # FastAPI 설정
        self.app = FastAPI()
        self.setup_api()
        
        # 시스템 상태 변수
        self.system_running = True
        self.camera_active = False
        self.current_feeding = False
        
        # 데이터 캐시 및 큐
        self.weight_cache = []
        self.event_queue = Queue()
        
        # 락
        self.camera_lock = threading.Lock()
        self.weight_lock = threading.Lock()
        self.feeding_lock = threading.Lock()
        
        # 마지막 작업 시간 기록
        self.last_times = {
            'weight': 0,
            'ultrasonic': 0,
            'schedule': 0,
            'error': 0
        }
        
        logger.info("PetFeeder initialized successfully")

    def load_config(self) -> dict:
        """설정 파일 로드"""
        try:
            with open('config/settings.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def setup_logger(self):
        """로거 설정"""
        logger.add(
            "logs/pet_feeder_{time}.log",
            rotation="1 day",
            retention="7 days",
            level="INFO"
        )

    def init_hardware(self):
        """하드웨어 컴포넌트 초기화"""
        try:
            self.ultrasonic = UltrasonicSensor(
                echo_pin=self.config['hardware']['ultrasonic']['echo_pin'],
                trigger_pin=self.config['hardware']['ultrasonic']['trigger_pin']
            )
            self.weight_sensor = WeightSensor(
                dout_pin=self.config['hardware']['weight_sensor']['dout_pin'],
                sck_pin=self.config['hardware']['weight_sensor']['sck_pin']
            )
            self.motor = MotorController(
                forward_pin=self.config['hardware']['motor']['forward_pin'],
                backward_pin=self.config['hardware']['motor']['backward_pin']
            )
            self.camera = CameraIMX219()
            
            logger.info("Hardware initialized successfully")
        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            raise

    def setup_api(self):
        """API 설정"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config['api']['allowed_origins'],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.websocket("/ws/camera")
        async def camera_websocket(websocket: WebSocket):
            await self.handle_camera_websocket(websocket)
            
        @self.app.post("/api/schedule/update")
        async def update_schedule(schedule: dict):
            return await self.handle_schedule_update(schedule)

    async def main_loop(self):
        """메인 모니터링 루프"""
        scheduler = RTOSScheduler()
        
        while self.system_running:
            try:
                current_time = time.time()
                task = scheduler.get_next_task(current_time)
                
                if task:
                    if task == 'ultrasonic':
                        await self.check_ultrasonic()
                    elif task == 'weight':
                        await self.monitor_weight()
                    elif task == 'schedule':
                        await self.check_feeding_schedule()
                    elif task == 'error':
                        await self.process_error_logs()
                    elif task == 'camera' and self.camera_active:
                        await self.process_camera_frame()
                    
                    scheduler.update_task_time(task, current_time)
                
                # 이벤트 큐 처리
                while not self.event_queue.empty():
                    event = self.event_queue.get()
                    await self.process_event(event)
                
                await asyncio.sleep(0.01)  # CPU 부하 방지
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await self.error_handler.log_error("main_loop", str(e))
                await asyncio.sleep(1)

    async def check_ultrasonic(self):
        """초음파 센서 확인"""
        try:
            distance = self.ultrasonic.get_distance()
            if distance is not None and distance <= 15:  # 15cm 이내 감지
                if not self.camera_active:
                    await self.start_camera_session()
        except Exception as e:
            logger.error(f"Ultrasonic sensor error: {e}")
            await self.error_handler.log_error("ultrasonic", str(e))

    async def monitor_weight(self):
        """무게 모니터링"""
        try:
            current_weight = self.weight_sensor.get_weight()
            if current_weight is not None:
                with self.weight_lock:
                    self.weight_cache.append((time.time(), current_weight))
                    
                    # 급격한 변화 감지
                    if len(self.weight_cache) >= 2:
                        await self.analyze_weight_change()
                    
                    # 사료 잔량 확인
                    if current_weight < self.config['feeding']['min_weight']:
                        self.event_queue.put({
                            'type': 'low_food',
                            'weight': current_weight
                        })
        except Exception as e:
            logger.error(f"Weight monitoring error: {e}")
            await self.error_handler.log_error("weight", str(e))

    async def start_camera_session(self):
        """카메라 세션 시작"""
        with self.camera_lock:
            if not self.camera_active:
                self.camera_active = True
                self.camera_session_start = time.time()
                
                # 별도 스레드에서 카메라 세션 실행
                threading.Thread(
                    target=lambda: self.camera.start_capture_session(
                        duration=180,  # 3분
                        interval=10    # 10초 간격
                    )
                ).start()

    def camera_processing(self):
        """카메라 이미지 캡처 및 처리"""
        try:
            start_time = time.time()
            images = []
            
            while time.time() - start_time < self.config['camera']['session_duration']:
                try:
                    result = self.camera.capture()
                    if result['status'] == 'success':
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        image_path = f"data/images/capture_{timestamp}.jpg"
                        # 이미지 저장 및 분석 로직
                        images.append(image_path)
                    
                    time.sleep(10)  # 10초 간격으로 캡처
                    
                except Exception as e:
                    logger.error(f"Camera capture error: {e}")
                    
            # 세션 종료 후 이미지 분석
            self.analyze_captured_images(images)
            
        finally:
            self.camera_active = False

    async def execute_feeding(self, amount: float):
        """사료 급여 실행"""
        with self.feeding_lock:
            if self.current_feeding:
                return
            
            self.current_feeding = True
            try:
                initial_weight = self.weight_sensor.get_weight()
                if initial_weight is None:
                    raise Exception("Weight sensor error")
                
                # 모터 제어로 사료 배출
                self.motor.start_feeding()
                
                # 목표 무게 도달할 때까지 대기
                while True:
                    current_weight = self.weight_sensor.get_weight()
                    if current_weight is None:
                        raise Exception("Weight sensor error during feeding")
                    
                    if current_weight - initial_weight >= amount:
                        break
                    
                    await asyncio.sleep(0.1)
                
                self.motor.stop_feeding()
                
                # 급여 결과 검증
                final_weight = self.weight_sensor.get_weight()
                if abs((final_weight - initial_weight) - amount) > self.config['feeding']['error_threshold']:
                    await self.error_handler.log_error(
                        "feeding",
                        f"Feeding amount error - Expected: {amount}g, Actual: {final_weight - initial_weight}g"
                    )
                
            except Exception as e:
                logger.error(f"Feeding error: {e}")
                await self.error_handler.log_error("feeding", str(e))
                self.motor.stop_feeding()  # 안전을 위해 모터 정지
                
            finally:
                self.current_feeding = False

    async def run(self):
        """시스템 실행"""
        try:
            logger.info("Starting PetFeeder system")
            
            # API 서버 시작 (별도 스레드)
            api_thread = threading.Thread(
                target=lambda: uvicorn.run(
                    self.app,
                    host=self.config['api']['host'],
                    port=self.config['api']['port']
                )
            )
            api_thread.start()
            
            # 메인 루프 실행
            await self.main_loop()
            
        except KeyboardInterrupt:
            logger.info("Shutting down PetFeeder system")
            await self.cleanup()
        except Exception as e:
            logger.error(f"System error: {e}")
            await self.cleanup()

    async def cleanup(self):
        """시스템 종료 및 정리"""
        self.system_running = False
        
        # 하드웨어 정리
        self.motor.cleanup()
        self.ultrasonic.cleanup()
        self.weight_sensor.cleanup()
        
        # 파일 정리
        await self.file_manager.cleanup()
        
        logger.info("System cleanup completed")

    async def process_camera_frame(self):
        """카메라 프레임 처리"""
        if not self.camera_active:
            return
        
        try:
            result = self.camera.capture()
            if result['status'] == 'success':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = f"data/images/capture_{timestamp}.jpg"
                
                # 웹소켓 클라이언트가 연결되어 있다면 프레임 전송
                if hasattr(self, 'websocket_clients'):
                    for client in self.websocket_clients:
                        try:
                            await client.send_bytes(result['frame'])
                        except:
                            continue
                
                # 3분 세션이 끝났는지 확인
                if time.time() - self.camera_session_start > 180:  # 3분
                    self.camera_active = False
                    await self.analyze_captured_images()
                
        except Exception as e:
            logger.error(f"Camera frame processing error: {e}")

if __name__ == "__main__":
    import uvicorn
    
    pet_feeder = PetFeeder()
    asyncio.run(pet_feeder.run())