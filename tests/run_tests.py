import os
import sys

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_motor import MotorTest
from test_weight import WeightSensorTest
from test_camera import IMX219LibcameraTest

def run_all_tests():
    tests = [
        ("모터", MotorTest),
        ("무게 센서", WeightSensorTest),
        ("카메라", IMX219LibcameraTest)
    ]
    
    results = []
    for name, test_class in tests:
        print(f"\n=== {name} 테스트 시작 ===")
        try:
            test = test_class()
            success = test.test_camera() if name == "카메라" else test.test_motor_control() if name == "모터" else test.test_weight_sensor()
            results.append((name, success))
        except Exception as e:
            print(f"테스트 실패: {str(e)}")
            results.append((name, False))
        finally:
            if 'test' in locals():
                test.cleanup()
    
    print("\n=== 테스트 결과 요약 ===")
    for name, success in results:
        print(f"{name}: {'성공' if success else '실패'}")

if __name__ == "__main__":
    run_all_tests() 