from app.hardware.ultrasonic import UltrasonicSensor
from time import sleep

# 센서 초기화 (echo=24, trigger=23)
sensor = UltrasonicSensor(
    echo_pin=24,
    trigger_pin=23,
    max_distance=1.0,         # 최대 1m
    threshold_distance=0.2    # 20cm = 0.2m
)

try:
    print("초음파 센서 테스트 시작 (Ctrl+C로 종료)")
    
    while True:
        try:
            # 거리 측정
            distance = sensor.get_distance()
            
            if distance is not None:
                print(f"거리: {distance:.1f} cm")
                
                # 20cm 미만일 때 경고
                if sensor.check_obstacle():
                    print("경고: 물체가 가까움!")
            
        except Exception as e:
            print(f"측정 실패: {str(e)}")
        
        sleep(1)
        
except KeyboardInterrupt:
    print("\n프로그램을 종료합니다.")
finally:
    sensor.cleanup()