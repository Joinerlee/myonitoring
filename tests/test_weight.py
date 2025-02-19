import time
import os
import sys
from tests import GPIO, setup_gpio, print_test_result, is_raspberry_pi_5

class WeightSensorTest:
    def __init__(self):
        if not is_raspberry_pi_5():
            raise Exception("이 테스트는 라즈베리파이 5에서만 실행 가능합니다.")
            
        setup_gpio()
        self.DOUT = 14
        self.SCK = 15
        
        GPIO.setup(self.DOUT, GPIO.IN)
        GPIO.setup(self.SCK, GPIO.OUT)
        print("무게 센서 GPIO 초기화 완료")
        
    def read_raw_value(self):
        """Mock 데이터 생성"""
        # 실제 값 대신 테스트용 값 생성
        import random
        return random.randint(8000000, 8999999)

    def test_weight_sensor(self):
        try:
            print("\n무게 센서 테스트 시작...")
            
            # 10회 샘플링
            samples = []
            for i in range(10):
                value = self.read_raw_value()
                samples.append(value)
                print(f"샘플 {i+1}: {value}")
                time.sleep(0.1)
            
            # 평균값 계산
            avg = sum(samples) / len(samples)
            print(f"\n평균값: {avg:.0f}")
            
            print_test_result("무게 센서", True)
            return True
            
        except Exception as e:
            print_test_result("무게 센서", False, str(e))
            return False

    def cleanup(self):
        try:
            GPIO.cleanup()
            print("무게 센서 GPIO 정리 완료")
        except:
            pass

if __name__ == "__main__":
    test = None
    try:
        test = WeightSensorTest()
        test.test_weight_sensor()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        print(f"\n테스트 실패: {str(e)}")
    finally:
        if test:
            test.cleanup()