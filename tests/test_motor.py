from gpiozero import Motor, PWMOutputDevice
from time import sleep, time

class PIDController:
    def __init__(self, kp, ki, kd, setpoint, max_output=0.6):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.max_output = max_output
        self.previous_error = 0
        self.integral = 0
        self.last_time = time()
        self.last_value = None

    def compute(self, current_value):
        # 목표값에 도달했는지 확인
        if abs(current_value - self.setpoint) < 0.1:
            return None

        # 현재 시간과 시간 간격 계산
        current_time = time()
        dt = current_time - self.last_time

        # 오차 계산
        error = self.setpoint - current_value

        # 급격한 변화 감지 및 대응
        if self.last_value is not None:
            value_change = abs(current_value - self.last_value)
            if value_change > 5:  # 급격한 변화 임계값
                self.integral = 0  # 적분항 리셋
                print(f"급격한 변화 감지! ({value_change:.1f}) - 제어 재조정")

        # 적분항 계산 (제한된 범위 내에서)
        self.integral = max(min(self.integral + error * dt, 5), -5)

        # 미분항 계산
        derivative = (error - self.previous_error) / dt if dt > 0 else 0

        # 기본 출력값 계산
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)

        # 오차 크기에 따른 속도 제한
        error_magnitude = abs(error)
        if error_magnitude > 10:
            speed_limit = self.max_output * 0.8  # 오차가 클 때는 80% 속도
        elif error_magnitude > 5:
            speed_limit = self.max_output * 0.6  # 중간 오차는 60% 속도
        else:
            speed_limit = self.max_output * 0.4  # 작은 오차는 40% 속도

        # 상태 업데이트
        self.previous_error = error
        self.last_time = current_time
        self.last_value = current_value

        # 출력값 제한
        return max(0, min(speed_limit, output))

# GPIO 핀 설정
motor = Motor(forward=17, backward=18)
speed = PWMOutputDevice(12)

# PID 컨트롤러 초기화 (더 높은 게인값 사용)
pid = PIDController(
    kp=0.05,   # 비례 게인
    ki=0.003,  # 적분 게인
    kd=0.02,   # 미분 게인
    setpoint=20,
    max_output=0.6  # 최대 60% 속도
)

try:
    print("모터 PID 제어 시작... (Ctrl+C로 중지)")
    print("목표값: 20")
    print("동작 모드:")
    print("- 오차 > 10: 최대 48% 속도")
    print("- 오차 > 5:  최대 36% 속도")
    print("- 오차 <= 5: 최대 24% 속도")
    motor.forward()
    
    while True:
        current_input = float(input("현재 입력값을 입력하세요: "))
        
        # PID 제어값 계산
        control_value = pid.compute(current_input)
        
        # 목표값 도달 시 모터 정지
        if control_value is None:
            print("목표값 도달! 모터를 정지합니다.")
            motor.stop()
            speed.off()
            break
        
        # 모터 속도 제어
        speed.value = control_value
        
        print(f"입력값: {current_input}, 모터 속도: {control_value*100:.1f}%")
        sleep(0.1)  # 제어 주기

except KeyboardInterrupt:
    print("\n모터 정지")
    motor.stop()
    speed.off()
except Exception as e:
    print(f"오류 발생: {e}")
    motor.stop()
    speed.off() 