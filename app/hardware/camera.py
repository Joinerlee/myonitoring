# from picamera2 import Picamera2  # 주석 처리
import subprocess
import os
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Optional, Dict

class CameraIMX219:
    """라즈베리파이 카메라 (IMX219) 제어 클래스"""
    
    def __init__(self, 
                 save_dir: str = "data/images",
                 resolution: tuple = (3840, 2160),  # 4K UHD
                 format: str = "jpg",
                 rotation: int = 0):
        """
        Args:
            save_dir (str): 이미지 저장 경로
            resolution (tuple): 해상도 (width, height)
            format (str): 이미지 포맷 (jpg/png)
            rotation (int): 카메라 회전 각도 (0/90/180/270)
        """
        try:
            print("[camera] 카메라 초기화 시작...")
            # 저장 디렉토리 생성
            self.save_dir = Path(save_dir)
            self.save_dir.mkdir(parents=True, exist_ok=True)
            print(f"[camera] 저장 경로 생성: {save_dir}")
            
            self.resolution = resolution
            self.format = format.lower()
            self.rotation = rotation
            
            print(f"[camera] 설정: {resolution} / {format} / 회전: {rotation}도")
            
            # libcamera 설정
            self.capture_config = {
                "width": resolution[0],
                "height": resolution[1],
                "rotation": rotation,
                "timeout": 2000,  # 2초 타임아웃
                "nopreview": True
            }
            
            # 카메라 테스트
            self._test_camera()
            self._is_initialized = True
            print("[camera] 초기화 완료")
            
        except Exception as e:
            print(f"[camera] 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def _test_camera(self) -> bool:
        """카메라 작동 테스트"""
        print("[camera] 카메라 테스트 중...")
        try:
            cmd = ["libcamera-still", "--list-cameras"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if "Available cameras" not in result.stdout:
                raise Exception("카메라를 찾을 수 없습니다")
            print("[camera] 카메라 테스트 성공")
            return True
        except Exception as e:
            print(f"[camera] 카메라 테스트 실패: {str(e)}")
            return False
    
    def capture(self) -> Dict:
        """
        단일 이미지 캡처
        Returns:
            Dict: {
                'status': 'success/error',
                'image_path': str,
                'message': str
            }
        """
        if not self._is_initialized:
            print("[camera] 카메라가 초기화되지 않았습니다")
            return {
                'status': 'error',
                'message': '카메라가 초기화되지 않았습니다'
            }
            
        try:
            print("[camera] 이미지 캡처 시작...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = self.save_dir / f"capture_{timestamp}.{self.format}"
            
            print(f"[camera] 저장 경로: {image_path}")
            
            # libcamera-still 명령어 구성
            cmd = [
                "libcamera-still",
                f"--width={self.resolution[0]}",
                f"--height={self.resolution[1]}",
                f"--rotation={self.rotation}",
                "--nopreview",
                "--immediate",
                f"--output={str(image_path)}"
            ]
            
            print(f"[camera] 명령어: {' '.join(cmd)}")
            
            # 이미지 캡처
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("[camera] 캡처 성공")
                return {
                    'status': 'success',
                    'image_path': str(image_path),
                    'message': '이미지 캡처 성공'
                }
            else:
                raise Exception(f"캡처 실패: {result.stderr}")
                
        except Exception as e:
            error_msg = str(e)
            print(f"[camera] 캡처 오류: {error_msg}")
            return {
                'status': 'error',
                'message': error_msg
            }
    
    def start_capture_session(self, duration: int = 180, interval: int = 10) -> list:
        """
        지정된 시간 동안 주기적으로 이미지 캡처
        Args:
            duration (int): 촬영 지속 시간 (초)
            interval (int): 촬영 간격 (초)
        Returns:
            list: 캡처된 이미지 경로 리스트
        """
        print(f"[camera] 캡처 세션 시작 (지속시간: {duration}초, 간격: {interval}초)")
        captured_images = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            print(f"[camera] 경과 시간: {int(time.time() - start_time)}초")
            result = self.capture()
            if result['status'] == 'success':
                captured_images.append(result['image_path'])
                print(f"[camera] 캡처 완료: {len(captured_images)}장 촬영됨")
            time.sleep(interval)
        
        print(f"[camera] 세션 종료. 총 {len(captured_images)}장 촬영")
        return captured_images
    
    def cleanup(self):
        """리소스 정리"""
        print("[camera] 리소스 정리")
        self._is_initialized = False