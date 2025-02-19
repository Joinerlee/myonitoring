from gpiozero import DigitalInputDevice, DigitalOutputDevice
import time
from typing import Optional, Tuple
import statistics
import json
import os

class WeightSensor:
    """HX711 무게 센서 클래스"""
    
    def __init__(self,
                 dout_pin: int = 14,
                 sck_pin: int = 15,
                 gain: int = 128,
                 calibration_file: str = 'weight_calibration.json'
                ):
        self.calibration_file = calibration_file
        try:
            print("[weight] 무게 센서 초기화 시작...")
            print(f"[weight] 설정: DOUT={dout_pin}, SCK={sck_pin}, GAIN={gain}")
            
            self.pd_sck = DigitalOutputDevice(sck_pin)
            self.dout = DigitalInputDevice(dout_pin)
            self.gain = 0
            self.reference_unit = -439.1079999999999
            self.offset = 0
            
            self.set_gain(gain)
            self._is_initialized = True
            
            if not self.load_calibration():
                print("[weight] 캘리브레이션 데이터가 없습니다. 영점 조정을 실행합니다...")
                self.tare()
            
            print("[weight] 초기화 완료")
            
        except Exception as e:
            print(f"[weight] 초기화 실패: {str(e)}")
            self._is_initialized = False

    def is_ready(self) -> bool:
        """센서 데이터 읽기 준비 상태 확인"""
        return not self.dout.value

    def set_gain(self, gain: int) -> None:
        """게인값 설정"""
        if gain == 128:
            self.gain = 1
        elif gain == 64:
            self.gain = 3
        else:
            raise ValueError("게인은 128 또는 64만 설정 가능합니다")
        
        self.pd_sck.off()
        self.read()

    def read(self) -> int:
        """원시 데이터 읽기"""
        while not self.is_ready():
            pass

        dataBits = [0] * 24
        for i in range(24):
            self.pd_sck.on()
            dataBits[i] = self.dout.value
            self.pd_sck.off()

        for _ in range(self.gain):
            self.pd_sck.on()
            self.pd_sck.off()

        dataBytes = 0
        for i in range(24):
            dataBytes = (dataBytes << 1) | dataBits[i]
        
        if dataBits[0]:
            dataBytes = dataBytes - (1 << 24)
            
        return dataBytes

    def read_average(self, times: int = 10) -> float:
        """평균값 읽기"""
        values = []
        for _ in range(times):
            values.append(self.read())
            time.sleep(0.1)
            
        if len(values) > 2:
            values = self._remove_outliers(values)
        return statistics.mean(values)

    def _remove_outliers(self, data: list, threshold: float = 2.0) -> list:
        """이상치 제거"""
        if len(data) < 3:
            return data
            
        mean = statistics.mean(data)
        std = statistics.stdev(data)
        
        return [x for x in data if abs(x - mean) <= threshold * std]

    def tare(self, times: int = 15) -> None:
        print(f"[weight] 영점 조정 시작 (샘플 수: {times})")
        self.offset = self.read_average(times)
        print("[weight] 영점 조정 완료")

    def get_weight(self) -> Optional[float]:
        if not self._is_initialized:
            print("[weight] 센서가 초기화되지 않았습니다")
            return None
            
        try:
            value = self.read_average() - self.offset
            weight = abs(value / self.reference_unit)
            
            print(f"[weight] 측정 무게: {weight:.1f}g")
            
            if weight > 1000:
                print("[weight] 비정상 무게 감지. 영점 조정을 실행합니다...")
                self.tare()
                value = self.read_average() - self.offset
                weight = abs(value / self.reference_unit)
                print(f"[weight] 재측정 무게: {weight:.1f}g")
            
            return weight
            
        except Exception as e:
            print(f"[weight] 무게 측정 실패: {str(e)}")
            return None

    def calibrate(self, known_weight: float, times: int = 15) -> Tuple[bool, float]:
        print(f"[weight] 캘리브레이션 시작 (기준 무게: {known_weight}g)")
        try:
            self.tare(times)
            measured_value = self.read_average(times)
            self.reference_unit = abs(measured_value / known_weight)
            print(f"[weight] 캘리브레이션 완료 (reference_unit: {self.reference_unit})")
            return True, self.reference_unit
        except Exception as e:
            print(f"[weight] 캘리브레이션 실패: {str(e)}")
            return False, 0

    def save_calibration(self) -> bool:
        """캘리브레이션 데이터 저장"""
        try:
            calibration_data = {
                'reference_unit': self.reference_unit,
                'offset': self.offset
            }
            with open(self.calibration_file, 'w') as f:
                json.dump(calibration_data, f)
            return True
        except Exception as e:
            print(f"캘리브레이션 데이터 저장 실패: {str(e)}")
            return False

    def load_calibration(self) -> bool:
        """저장된 캘리브레이션 데이터 로드"""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                self.reference_unit = data['reference_unit']
                self.offset = data['offset']
                return True
            return False
        except Exception as e:
            print(f"캘리브레이션 데이터 로드 실패: {str(e)}")
            return False

    def cleanup(self):
        """센서 리소스 정리"""
        if self._is_initialized:
            self.pd_sck.close()
            self.dout.close()
            self._is_initialized = False
