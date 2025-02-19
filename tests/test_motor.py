import RPi.GPIO as GPIO
import time
import os
import sys

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests import setup_gpio, print_test_result, is_raspberry_pi_5

class MotorTest:
    def __init__(self):
        if not is_raspberry_pi_5():
            raise Exception("이 테스트는 라즈베리파이 5에서만 실행 가능합니다.")
            
        setup_gpio()
        self.MOTOR_FORWARD = 17
        self.MOTOR_BACKWARD = 18
        self.MOTOR_SPEED = 12
        
        # PWM 설정 (라즈베리파이 5는 하드웨어 PWM 지원)
        GPIO.setup(self.MOTOR_FORWARD, GPIO.OUT)
        GPIO.setup(self.MOTOR_BACKWARD, GPIO.OUT)
        GPIO.setup(self.MOTOR_SPEED, GPIO.OUT)
        self.pwm = GPIO.PWM(self.MOTOR_SPEED, 1000)  # 1kHz
        self.pwm.start(0)

    def test_motor_control(self):
        try:
            print("\n모터 제어 테스트 시작...")
            
            # 정방향 테스트
            print("1. 정방향 회전 테스트")
            GPIO.output(self.MOTOR_FORWARD, GPIO.HIGH)
            GPIO.output(self.MOTOR_BACKWARD, GPIO.LOW)
            
            # 속도 변화 테스트
            for speed in [20, 40, 60, 80, 100]:
                print(f"속도: {speed}%")
                self.pwm.ChangeDutyCycle(speed)
                time.sleep(1)
            
            # 정지
            self.pwm.ChangeDutyCycle(0)
            GPIO.output(self.MOTOR_FORWARD, GPIO.LOW)
            
            print_test_result("모터 제어", True)
            return True
            
        except Exception as e:
            print_test_result("모터 제어", False, str(e))
            return False
        
    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        test = MotorTest()
        test.test_motor_control()
    finally:
        test.cleanup() 