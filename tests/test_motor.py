import RPi.GPIO as GPIO
import time

class MotorTest:
    def __init__(self):
        # GPIO 설정
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # 핀 번호 설정
        self.MOTOR_FORWARD = 17
        self.MOTOR_BACKWARD = 18
        self.MOTOR_SPEED = 12
        
        # GPIO 초기화
        GPIO.setup(self.MOTOR_FORWARD, GPIO.OUT)
        GPIO.setup(self.MOTOR_BACKWARD, GPIO.OUT)
        GPIO.setup(self.MOTOR_SPEED, GPIO.OUT)
        
        # PWM 설정 (라즈베리파이 5의 하드웨어 PWM 사용)
        self.pwm = GPIO.PWM(self.MOTOR_SPEED, 1000)  # 1kHz
        self.pwm.start(0)
        print("모터 GPIO 초기화 완료")

    def test_motor_control(self):
        try:
            print("\n=== 모터 제어 테스트 시작 ===")
            
            # 1. 정방향 저속 회전
            print("\n1. 정방향 저속 (30%)")
            GPIO.output(self.MOTOR_FORWARD, GPIO.HIGH)
            GPIO.output(self.MOTOR_BACKWARD, GPIO.LOW)
            self.pwm.ChangeDutyCycle(30)
            time.sleep(3)
            
            # 2. 정방향 중속 회전
            print("\n2. 정방향 중속 (60%)")
            self.pwm.ChangeDutyCycle(60)
            time.sleep(3)
            
            # 3. 정방향 고속 회전
            print("\n3. 정방향 고속 (90%)")
            self.pwm.ChangeDutyCycle(90)
            time.sleep(3)
            
            # 4. 정지
            print("\n4. 모터 정지")
            self.pwm.ChangeDutyCycle(0)
            GPIO.output(self.MOTOR_FORWARD, GPIO.LOW)
            time.sleep(1)
            
            # 5. 역방향 테스트
            print("\n5. 역방향 테스트 (50%)")
            GPIO.output(self.MOTOR_FORWARD, GPIO.LOW)
            GPIO.output(self.MOTOR_BACKWARD, GPIO.HIGH)
            self.pwm.ChangeDutyCycle(50)
            time.sleep(3)
            
            # 최종 정지
            self.pwm.ChangeDutyCycle(0)
            GPIO.output(self.MOTOR_BACKWARD, GPIO.LOW)
            print("\n테스트 완료!")
            return True
            
        except Exception as e:
            print(f"\n테스트 실패: {str(e)}")
            return False
        
    def cleanup(self):
        try:
            self.pwm.stop()
            GPIO.cleanup()
            print("GPIO 정리 완료")
        except:
            pass

def main():
    test = None
    try:
        test = MotorTest()
        test.test_motor_control()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    finally:
        if test:
            test.cleanup()

if __name__ == "__main__":
    main() 