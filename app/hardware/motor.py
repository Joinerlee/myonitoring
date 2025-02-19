# app/hardware/motor.py
import logging
import os

# GPIO 선택적 임포트
if os.environ.get('MOCK_GPIO', 'true').lower() == 'true':
    from .gpio_mock import GPIOMock as GPIO
else:
    import RPi.GPIO as GPIO
import time

logger = logging.getLogger(__name__)

class MotorController:
    def __init__(self, forward_pin=17, backward_pin=18, speed_pin=12):
        self.forward_pin = forward_pin
        self.backward_pin = backward_pin
        self.speed_pin = speed_pin
        
        # GPIO 설정
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # 핀 설정
        GPIO.setup(self.forward_pin, GPIO.OUT)
        GPIO.setup(self.backward_pin, GPIO.OUT)
        GPIO.setup(self.speed_pin, GPIO.OUT)
        
        # PWM 설정
        self.pwm = GPIO.PWM(self.speed_pin, 1000)  # 1kHz
        self.pwm.start(0)
        logger.info("모터 컨트롤러 초기화 완료")

    def set_speed(self, speed):
        """모터 속도 설정 (0-100)"""
        self.pwm.ChangeDutyCycle(speed)
        logger.debug(f"모터 속도 설정: {speed}%")

    def forward(self, speed=50):
        """정방향 회전"""
        GPIO.output(self.forward_pin, GPIO.HIGH)
        GPIO.output(self.backward_pin, GPIO.LOW)
        self.set_speed(speed)
        logger.info(f"모터 정방향 회전 (속도: {speed}%)")

    def backward(self, speed=50):
        """역방향 회전"""
        GPIO.output(self.forward_pin, GPIO.LOW)
        GPIO.output(self.backward_pin, GPIO.HIGH)
        self.set_speed(speed)
        logger.info(f"모터 역방향 회전 (속도: {speed}%)")

    def stop(self):
        """모터 정지"""
        self.set_speed(0)
        GPIO.output(self.forward_pin, GPIO.LOW)
        GPIO.output(self.backward_pin, GPIO.LOW)
        logger.info("모터 정지")

    def cleanup(self):
        """리소스 정리"""
        self.stop()
        self.pwm.stop()
        logger.info("모터 리소스 정리 완료")
                                    