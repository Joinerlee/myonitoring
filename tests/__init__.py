import RPi.GPIO as GPIO
import sys
import os

# 라즈베리파이 5 확인
def is_raspberry_pi_5():
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi 5' in model
    except:
        return False

# GPIO 기본 설정
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

# 테스트 결과 출력 형식
def print_test_result(test_name, success, message=""):
    print(f"\n{'='*50}")
    print(f"테스트: {test_name}")
    print(f"결과: {'성공' if success else '실패'}")
    if message:
        print(f"메시지: {message}")
    print('='*50)
