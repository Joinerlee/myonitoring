from gpiozero import DigitalInputDevice, DigitalOutputDevice
import time

class HX711:
    def __init__(self, dout_pin, pd_sck_pin, gain=128):
        self.pd_sck = DigitalOutputDevice(pd_sck_pin)
        self.dout = DigitalInputDevice(dout_pin)
        
        self.GAIN = 0
        self.REFERENCE_UNIT = 1
        self.OFFSET = 0
        
        self.set_gain(gain)
        print(f"DOUT핀: GPIO{dout_pin} (물리적 핀: {self._get_physical_pin(dout_pin)})")
        print(f"SCK핀: GPIO{pd_sck_pin} (물리적 핀: {self._get_physical_pin(pd_sck_pin)})")

    def _get_physical_pin(self, gpio):
        mapping = {
            14: 8,   # DOUT
            15: 10,  # SCK
        }
        return mapping.get(gpio, "알 수 없음")

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

    def read_average(self, times=3):
        total = 0
        for _ in range(times):
            total += self.read()
            time.sleep(0.1)
        return total / times

    def get_value(self):
        return self.read_average() - self.OFFSET

    def get_weight(self):
        value = self.get_value()
        value = value / self.REFERENCE_UNIT
        return value

    def tare(self, times=15):
        print("영점 조정 중...")
        self.OFFSET = self.read_average(times)
        print(f"영점: {self.OFFSET}")

    def set_reference_unit(self, reference_unit):
        self.REFERENCE_UNIT = reference_unit

def calibrate(hx):
    print("\n=== 캘리브레이션 시작 ===")
    input("1. 로드셀에서 모든 무게를 제거하고 Enter를 누르세요")
    hx.tare()
    
    known_weight = float(input("2. 캘리브레이션에 사용할 물체의 무게(g)를 입력하세요: "))
    input("3. 이제 그 물체를 로드셀 위에 올리고 Enter를 누르세요")
    
    measured_value = hx.get_value()
    reference_unit = measured_value / known_weight
    hx.set_reference_unit(reference_unit)
    
    print(f"\n캘리브레이션 완료!")
    print(f"Reference unit: {reference_unit}")
    return reference_unit

if __name__ == "__main__":
    try:
        DOUT_PIN = 14  # GPIO14 (물리적 핀 8)
        SCK_PIN = 15   # GPIO15 (물리적 핀 10)

        print("HX711 초기화 중...")
        hx = HX711(DOUT_PIN, SCK_PIN)
        
        # 캘리브레이션 수행
        reference_unit = calibrate(hx)
        
        print("\n무게 측정 시작...")
        while True:
            try:
                weight = hx.get_weight()
                print(f"무게: {weight:.1f}g")
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n프로그램 종료")
                break
            except Exception as e:
                print(f"에러 발생: {e}")
                continue
                
    finally:
        hx.pd_sck.close()
        hx.dout.close()