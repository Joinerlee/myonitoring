from gpiozero import DigitalInputDevice, DigitalOutputDevice
import time
from typing import Optional, Tuple
import statistics
import json
import os

class WeightSensor:
    """HX711 무게 센서 클래스"""
    
    def __init__(self, dout_pin=14, sck_pin=15, gain=128):
        try:
            print("[weight] 무게 센서 초기화 시작...")
            print(f"[weight] 설정: DOUT={dout_pin}, SCK={sck_pin}, GAIN={gain}")
            
            self.pd_sck = DigitalOutputDevice(sck_pin)
            self.dout = DigitalInputDevice(dout_pin)
            
            self.GAIN = 0
            self.REFERENCE_UNIT = 1
            self.OFFSET = 0
            
            self.set_gain(gain)
            self._is_initialized = True
            
            # 영점 조정
            print("[weight] 캘리브레이션 데이터가 없습니다. 영점 조정을 실행합니다...")
            self.tare()
            print("[weight] 초기화 완료")
            
        except Exception as e:
            print(f"[weight] 초기화 실패: {str(e)}")
            self._is_initialized = False

    def is_ready(self):
        return self.dout.value == 0

    def set_gain(self, gain):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        else:
            raise ValueError("게인은 128 또는 64만 설정 가능합니다.")
        
        self.pd_sck.off()
        self.read()

    def read(self):
        while not self.is_ready():
            pass

        dataBits = [0] * 24
        for i in range(24):
            self.pd_sck.on()
            dataBits[i] = self.dout.value
            self.pd_sck.off()

        for i in range(self.GAIN):
            self.pd_sck.on()
            self.pd_sck.off()

        dataBytes = 0
        for i in range(24):
            dataBytes = (dataBytes << 1) | dataBits[i]

        if dataBits[0]:
            dataBytes = dataBytes - (1 << 24)

        return dataBytes

    def get_weight(self):
        if not self._is_initialized:
            print("[weight] 센서가 초기화되지 않았습니다")
            return None
            
        try:
            value = self.read_average() - self.OFFSET
            value = value / self.REFERENCE_UNIT
            return value
        except Exception as e:
            print(f"[weight] 무게 측정 실패: {str(e)}")
            return None

    def read_average(self, times=3):
        total = 0
        for _ in range(times):
            total += self.read()
            time.sleep(0.1)
        return total / times

    def tare(self, times=15):
        print("[weight] 영점 조정 시작 (샘플 수: {times})")
        self.OFFSET = self.read_average(times)
        print("[weight] 영점 조정 완료")

    def calibrate(self, known_weight: float, times: int = 15) -> Tuple[bool, float]:
        print(f"[weight] 캘리브레이션 시작 (기준 무게: {known_weight}g)")
        try:
            self.tare(times)
            measured_value = self.read_average(times)
            self.REFERENCE_UNIT = abs(measured_value / known_weight)
            print(f"[weight] 캘리브레이션 완료 (reference_unit: {self.REFERENCE_UNIT})")
            return True, self.REFERENCE_UNIT
        except Exception as e:
            print(f"[weight] 캘리브레이션 실패: {str(e)}")
            return False, 0

    def save_calibration(self) -> bool:
        """캘리브레이션 데이터 저장"""
        try:
            calibration_data = {
                'reference_unit': self.REFERENCE_UNIT,
                'offset': self.OFFSET
            }
            with open('weight_calibration.json', 'w') as f:
                json.dump(calibration_data, f)
            return True
        except Exception as e:
            print(f"캘리브레이션 데이터 저장 실패: {str(e)}")
            return False

    def load_calibration(self) -> bool:
        """저장된 캘리브레이션 데이터 로드"""
        try:
            if os.path.exists('weight_calibration.json'):
                with open('weight_calibration.json', 'r') as f:
                    data = json.load(f)
                self.REFERENCE_UNIT = data['reference_unit']
                self.OFFSET = data['offset']
                return True
            return False
        except Exception as e:
            print(f"캘리브레이션 데이터 로드 실패: {str(e)}")
            return False

    def cleanup(self):
        if hasattr(self, 'pd_sck'):
            self.pd_sck.close()
        if hasattr(self, 'dout'):
            self.dout.close()
