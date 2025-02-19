import sys
import os
from unittest.mock import MagicMock

# GPIO Mock 설정
class GPIOMock:
    BCM = "BCM"
    OUT = "OUT"
    IN = "IN"
    HIGH = 1
    LOW = 0
    
    def __init__(self):
        self.mode = None
        self.warnings = True
        self.pins = {}
    
    def setmode(self, mode):
        self.mode = mode
    
    def setwarnings(self, state):
        self.warnings = state
    
    def setup(self, pin, mode):
        self.pins[pin] = {"mode": mode, "value": 0}
    
    def output(self, pin, value):
        if pin in self.pins:
            self.pins[pin]["value"] = value
    
    def input(self, pin):
        if pin in self.pins:
            # 테스트를 위해 무작위 값 반환
            import random
            return random.randint(0, 1)
        return 0
    
    def cleanup(self):
        self.pins.clear()
    
    def PWM(self, pin, freq):
        return PWMMock(pin, freq)

class PWMMock:
    def __init__(self, pin, freq):
        self.pin = pin
        self.freq = freq
        self.duty_cycle = 0
        self.running = False
    
    def start(self, dc):
        self.duty_cycle = dc
        self.running = True
    
    def ChangeDutyCycle(self, dc):
        self.duty_cycle = dc
    
    def stop(self):
        self.running = False

# GPIO Mock 객체 생성
GPIO = GPIOMock()

def is_raspberry_pi_5():
    """테스트 환경에서는 항상 True 반환"""
    return True

def setup_gpio():
    """Mock GPIO 설정"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

def print_test_result(test_name, success, message=""):
    print(f"\n{'='*50}")
    print(f"테스트: {test_name}")
    print(f"결과: {'성공' if success else '실패'}")
    if message:
        print(f"메시지: {message}")
    print('='*50)
