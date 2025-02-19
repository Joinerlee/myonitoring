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

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import logging

from hardware import MotorController, CameraIMX219, UltrasonicSensor, WeightSensor
from utils.error_handler import ErrorHandler
from utils.file_manager import FileManager
from core.task_scheduler import RTOSScheduler

# GPIO 에뮬레이션 모드
os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

# 한글 출력을 위한 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')  # 한국어 로케일 설정

# 로깅 설정 (파일 상단)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/pet_feeder.log', encoding='utf-8', mode='a')
    ]
)

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 핸들러 포맷 설정
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 스트림 핸들러 설정
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

# 파일 핸들러 설정
file_handler = logging.FileHandler('logs/pet_feeder.log', encoding='utf-8', mode='a')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 기존 핸들러 제거 후 새로운 핸들러 추가
logger.handlers = []
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / 'app'

# 필요한 디렉토리 생성
LOGS_DIR = APP_DIR / 'logs'
DATA_DIR = APP_DIR / 'data'
IMAGES_DIR = DATA_DIR / 'images'

for directory in [LOGS_DIR, DATA_DIR, IMAGES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class PetFeeder:
    def __init__(self):
        # 시스템 설정 로드
        self.config = self.load_config()
        
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
            'error': 0,
            'distance_print': 0,
            'weight_print': 0
        }
        
        logger.info("PetFeeder initialized successfully")

    def load_config(self) -> dict:
        """설정 파일 로드"""
        try:
            config_path = Path("config/settings.json")
            if not config_path.exists():
                print("[system] 설정 파일이 없습니다. 기본 설정을 사용합니다.")
                return {
                    "hardware": {
                        "ultrasonic": {
                            "echo_pin": 24,
                            "trigger_pin": 23,
                            "max_distance": 1.0,
                            "threshold_distance": 0.15
                        },
                        "weight_sensor": {
                            "dout_pin": 14,
                            "sck_pin": 15,
                            "gain": 128
                        },
                        "motor": {
                            "forward_pin": 23,
                            "backward_pin": 22,
                            "default_speed": 0.7
                        },
                        "camera": {
                            "resolution": [3840, 2160],
                            "format": "jpg",
                            "rotation": 0,
                            "session_duration": 180,
                            "capture_interval": 10
                        }
                    },
                    "api": {
                        "host": "0.0.0.0",
                        "port": 8000,
                        "allowed_origins": ["*"]
                    },
                    "feeding": {
                        "min_weight": 100,
                        "error_threshold": 10
                    }
                }
            
            with open(config_path, 'r') as f:
                config = json.load(f)
                print("[system] 설정 파일을 로드했습니다")
                return config
            
        except Exception as e:
            print(f"[system] 설정 파일 로드 실패: {str(e)}")
            raise

    def init_hardware(self):
        """하드웨어 컴포넌트 초기화"""
        try:
            self.motor = MotorController()
            self.camera = CameraIMX219()
            self.ultrasonic = UltrasonicSensor()
            self.weight_sensor = WeightSensor()
            
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
        logger.info("\n=== 시스템 시작 ===")
        logger.info("작업 간격:")
        logger.info("  - 초음파 센서: 100ms")
        logger.info("  - 무게 센서: 100ms")
        logger.info("  - 스케줄 확인: 1s")
        logger.info("  - 에러 로그 확인: 5s")
        logger.info("  - 카메라 프레임: 500ms (활성화시)\n")
        
        loop_count = 0
        status_interval = 10  # 10회마다 상태 출력 (더 자주 출력하도록 수정)
        
        logger.info("모니터링 시작...")
        
        while self.system_running:
            try:
                current_time = time.time()
                
                # 상태 출력 (더 자주)
                loop_count += 1
                if loop_count % status_interval == 0:
                    logger.info(f"\n=== 시스템 상태 (루프 {loop_count}) ===")
                    if self.weight_cache:
                        latest_weight = self.weight_cache[-1][1]
                        logger.info(f"현재 무게: {latest_weight:.1f}g")
                    logger.info(f"카메라 상태: {'활성화' if self.camera_active else '비활성화'}")
                    logger.info(f"급여 상태: {'급여중' if self.current_feeding else '대기중'}")
                
                # 작업 실행
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
                
                # 짧은 대기 시간
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"오류 발생: {str(e)}")
                await asyncio.sleep(1)

    async def check_ultrasonic(self):
        """초음파 센서 확인"""
        try:
            distance = self.ultrasonic.get_distance()
            if distance is not None:
                if distance <= 15:  # 15cm 이내 감지
                    logger.info(f"\n물체 감지! (거리: {distance:.1f}cm)")
                    if not self.camera_active:
                        logger.info("카메라 세션 시작...")
                        await self.start_camera_session()
                else:
                    # 매번 출력하지 말고 1초에 한 번만 출력
                    current_time = time.time()
                    if current_time - self.last_times.get('distance_print', 0) >= 1:
                        if distance < 50:  # 50cm 이내일 때만 거리 출력
                            logger.info(f"[초음파] 현재 거리: {distance:.1f}cm")
                        self.last_times['distance_print'] = current_time
        except Exception as e:
            logger.error(f"초음파 센서 오류: {str(e)}")

    async def monitor_weight(self):
        """무게 모니터링"""
        try:
            current_weight = self.weight_sensor.get_weight()
            if current_weight is not None:
                current_time = time.time()
                # 1초에 한 번만 무게 출력
                if current_time - self.last_times.get('weight_print', 0) >= 1:
                    logger.info(f"[무게] 현재 무게: {current_weight:.1f}g")
                    self.last_times['weight_print'] = current_time
                
                with self.weight_lock:
                    self.weight_cache.append((current_time, current_weight))
                    
                    # 사료 잔량 확인
                    if current_weight < self.config['feeding']['min_weight']:
                        logger.warning(f"사료 잔량 부족 ({current_weight:.1f}g)")
                        
        except Exception as e:
            logger.error(f"무게 센서 오류: {str(e)}")

    async def start_camera_session(self):
        """카메라 세션 시작"""
        with self.camera_lock:
            if not self.camera_active:
                self.camera_active = True
                self.camera_session_start = time.time()
                logger.info("3분간 촬영을 시작합니다 (10초 간격)")
                
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
                logger.info(f"[카메라] 이미지 저장: {image_path}")
                
                # 웹소켓 클라이언트가 연결되어 있다면 프레임 전송
                if hasattr(self, 'websocket_clients'):
                    for client in self.websocket_clients:
                        try:
                            await client.send_bytes(result['frame'])
                        except:
                            continue
                
                # 3분 세션이 끝났는지 확인
                elapsed_time = time.time() - self.camera_session_start
                if elapsed_time > 180:  # 3분
                    logger.info("\n카메라 세션 종료")
                    logger.info("촬영된 이미지 분석 시작...")
                    self.camera_active = False
                    await self.analyze_captured_images()
                else:
                    remaining = 180 - elapsed_time
                    logger.info(f"[카메라] 남은 시간: {int(remaining)}초")
                
        except Exception as e:
            logger.error(f"카메라 프레임 처리 오류: {str(e)}")

    async def check_feeding_schedule(self):
        """급여 스케줄 확인"""
        try:
            logger.info("[system] 급여 스케줄 확인 중...")
            current_time = datetime.now().strftime("%H:%M")
            
            with open('app/schedule/feeding_schedule.json', 'r') as f:
                schedule = json.load(f)
                
            for feeding in schedule['feedings']:
                if feeding['time'] == current_time:
                    if not self.current_feeding:
                        logger.info(f"[system] 급여 시간입니다: {current_time}")
                        await self.execute_feeding(feeding['amount'])
                        
        except Exception as e:
            logger.error(f"[system] 스케줄 확인 실패: {str(e)}")
            await self.error_handler.log_error("schedule", str(e))

def main():
    try:
        pet_feeder = PetFeeder()
        asyncio.run(pet_feeder.run())
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
    except Exception as e:
        logger.error(f"프로그램 오류: {str(e)}")

if __name__ == "__main__":
    if os.geteuid() != 0:
        logger.error("이 프로그램은 root 권한으로 실행해야 합니다.")
        sys.exit(1)
    main()