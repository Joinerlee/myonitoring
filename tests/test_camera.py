# tests/test_camera.py
import subprocess
import time
import os
from pathlib import Path
from tests import print_test_result, is_raspberry_pi_5

class IMX219LibcameraTest:
    def __init__(self):
        if not is_raspberry_pi_5():
            raise Exception("이 테스트는 라즈베리파이 5에서만 실행 가능합니다.")
        
        # 이미지 저장 디렉토리 생성
        self.image_dir = Path("test_images")
        self.image_dir.mkdir(exist_ok=True)
        
        # libcamera 설치 확인
        self._check_libcamera()
        print("IMX219 카메라 초기화 완료")

    def _check_libcamera(self):
        """libcamera 설치 확인"""
        try:
            subprocess.run(['libcamera-still', '--version'], 
                         capture_output=True, text=True, check=True)
        except:
            raise Exception("libcamera-still이 설치되어 있지 않습니다.")

    def capture_image(self, filename, exposure=20000, gain=1.0):
        """libcamera-still을 사용한 이미지 캡처"""
        output_path = self.image_dir / filename
        
        cmd = [
            'libcamera-still',
            '--width', '3280',
            '--height', '2464',
            '--exposure', str(exposure),
            '--gain', str(gain),
            '--awb', 'auto',
            '--denoise', 'off',
            '--output', str(output_path),
            '--immediate'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"이미지 캡처 실패: {result.stderr}")
        
        return output_path

    def test_camera(self):
        try:
            print("\n=== IMX219 Libcamera 테스트 시작 ===")
            print("해상도: 3280x2464 (8MP)")
            print("센서: Sony IMX219")
            
            # 다양한 설정으로 5장 촬영
            test_configs = [
                {"exposure": 20000, "gain": 1.0},  # 기본 설정
                {"exposure": 10000, "gain": 2.0},  # 짧은 노출, 높은 게인
                {"exposure": 30000, "gain": 1.0},  # 긴 노출
                {"exposure": 20000, "gain": 1.5},  # 중간 게인
                {"exposure": 15000, "gain": 1.8}   # 혼합 설정
            ]
            
            for i, config in enumerate(test_configs, 1):
                print(f"\n촬영 {i}/5 시작...")
                print(f"설정: 노출={config['exposure']}μs, 게인={config['gain']}")
                
                filename = f"imx219_libcamera_test_{i}.jpg"
                output_path = self.capture_image(
                    filename,
                    exposure=config['exposure'],
                    gain=config['gain']
                )
                
                print(f"이미지 저장: {output_path}")
                time.sleep(1)
            
            print("\n테스트 완료!")
            print_test_result("IMX219 Libcamera", True)
            return True
            
        except Exception as e:
            print_test_result("IMX219 Libcamera", False, str(e))
            return False

    def cleanup(self):
        """테스트 이미지 정리 (선택적)"""
        try:
            # 테스트 후 이미지 파일 유지하려면 이 부분 주석 처리
            # for file in self.image_dir.glob("imx219_libcamera_test_*.jpg"):
            #     file.unlink()
            # self.image_dir.rmdir()
            print("카메라 테스트 완료")
        except:
            pass

if __name__ == "__main__":
    test = None
    try:
        test = IMX219LibcameraTest()
        test.test_camera()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        print(f"\n테스트 실패: {str(e)}")
    finally:
        if test:
            test.cleanup()
