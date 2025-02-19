import RPi.GPIO as GPIO
import time
from tests import setup_gpio, print_test_result, is_raspberry_pi_5

class WeightSensorTest:
    def __init__(self):
        if not is_raspberry_pi_5():
            raise Exception("이 테스트는 라즈베리파이 5에서만 실행 가능합니다.")
            
        setup_gpio()
        self.DOUT = 14
        self.SCK = 15
        
        GPIO.setup(self.DOUT, GPIO.IN)
        GPIO.setup(self.SCK, GPIO.OUT)
        
    def read_raw_value(self):
        # HX711 프로토콜에 따른 데이터 읽기
        while GPIO.input(self.DOUT) == 1:
            time.sleep(0.01)
            
        data = 0
        for i in range(24):
            GPIO.output(self.SCK, GPIO.HIGH)
            time.sleep(0.000001)  # 1μs
            GPIO.output(self.SCK, GPIO.LOW)
            time.sleep(0.000001)
            data = (data << 1) | GPIO.input(self.DOUT)
            
        GPIO.output(self.SCK, GPIO.HIGH)
        time.sleep(0.000001)
        GPIO.output(self.SCK, GPIO.LOW)
        
        return data

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
            
            print_test_result("무게 센서", True)
            return True
            
        except Exception as e:
            print_test_result("무게 센서", False, str(e))
            return False

    def cleanup(self):
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        test = WeightSensorTest()
        test.test_weight_sensor()
    finally:
        test.cleanup()