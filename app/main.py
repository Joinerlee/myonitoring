# app/main.py

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from hardware import MotorController, CameraIMX219, UltrasonicSensor, WeightSensor
from core.task_scheduler import RTOSScheduler
from core.task_executor import TaskExecutor
from core.firebase_manager import FirebaseManager
from models.eye_detection import EyeDetectionModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/pet_feeder.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# GPIO 모드 설정
if os.environ.get('TESTING', 'false').lower() == 'true':
    # 테스트 환경: GPIO Mock 사용
    os.environ['MOCK_GPIO'] = 'true'
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'
    ROOT_CHECK_DISABLED = True
else:
    # 운영 환경: 실제 GPIO 사용
    os.environ['MOCK_GPIO'] = 'false'
    ROOT_CHECK_DISABLED = False

class PetFeeder:
    def __init__(self):
        """시스템 초기화"""
        self.config = self._load_config()
        self._init_directories()
        self._init_hardware()
        self._init_components()
        self._init_api()
        
        self.running = True
        logger.info("시스템 초기화 완료")

    def _load_config(self) -> dict:
        """설정 파일 로드"""
        try:
            with open("app/config/settings.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise

    def _init_directories(self):
        """필요한 디렉토리 생성"""
        dirs = ["logs", "data/images"]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def _init_hardware(self):
        """하드웨어 컴포넌트 초기화"""
        try:
            self.motor = MotorController()
            self.camera = CameraIMX219()
            self.ultrasonic = UltrasonicSensor()
            self.weight_sensor = WeightSensor()
            logger.info("하드웨어 초기화 완료")
        except Exception as e:
            logger.error(f"하드웨어 초기화 실패: {e}")
            raise

    def _init_components(self):
        """시스템 컴포넌트 초기화"""
        self.scheduler = RTOSScheduler()
        self.task_executor = TaskExecutor(self.scheduler)
        self.firebase = FirebaseManager()
        self.eye_detector = EyeDetectionModel()
        
        # 시스템 상태
        self.camera_active = False
        self.feeding_in_progress = False

    def _init_api(self):
        """API 서버 초기화"""
        self.app = FastAPI()
        
        # CORS 설정
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 라우트 설정
        self._setup_routes()

    def _setup_routes(self):
        """API 라우트 설정"""
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket(websocket)

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}

    async def _handle_websocket(self, websocket: WebSocket):
        """웹소켓 연결 처리"""
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                # 웹소켓 메시지 처리 로직
                await websocket.send_text(f"Message received: {data}")
        except Exception as e:
            logger.error(f"웹소켓 오류: {e}")

    async def main_loop(self):
        """메인 시스템 루프"""
        logger.info("시스템 모니터링 시작")
        
        while self.running:
            try:
                # 초음파 센서 확인
                if await self.task_executor.execute_task("ultrasonic"):
                    if not self.camera_active:
                        await self._start_camera_session()

                # 무게 센서 모니터링
                await self.task_executor.execute_task("weight")

                # 급여 스케줄 확인
                await self.task_executor.execute_task("feeding")

                await asyncio.sleep(0.1)  # 100ms 대기

            except Exception as e:
                logger.error(f"시스템 오류: {e}")
                await asyncio.sleep(1)

    async def _start_camera_session(self):
        """카메라 세션 시작"""
        if not self.camera_active:
            self.camera_active = True
            logger.info("카메라 세션 시작")
            
            try:
                images = await self.camera.start_capture_session()
                if images:
                    results = self.eye_detector.batch_process(images)
                    if results:
                        await self.firebase.save_detection_result(results)
            finally:
                self.camera_active = False

    async def run(self):
        """시스템 실행"""
        try:
            await self.main_loop()
        except KeyboardInterrupt:
            logger.info("시스템 종료 요청")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """시스템 종료 및 리소스 정리"""
        self.running = False
        
        # 하드웨어 정리
        self.motor.cleanup()
        self.ultrasonic.cleanup()
        self.weight_sensor.cleanup()
        self.camera.cleanup()
        
        logger.info("시스템 종료 완료")

def main():
    """메인 함수"""
    try:
        # root 권한 체크 (테스트 환경에서는 스킵)
        if not ROOT_CHECK_DISABLED and os.geteuid() != 0:
            logger.error("이 프로그램은 root 권한으로 실행해야 합니다.")
            logger.error("테스트 시에는 'TESTING=true python app/main.py'로 실행하세요.")
            sys.exit(1)
            
        pet_feeder = PetFeeder()
        asyncio.run(pet_feeder.run())
        
    except Exception as e:
        logger.error(f"프로그램 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()