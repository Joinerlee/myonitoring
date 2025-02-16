from app.hardware.ultrasonic import UltrasonicSensor
import time

def main():
    # 센서 초기화 (30cm 제한)
    sensor = UltrasonicSensor(
        echo_pin=18,
        trigger_pin=17,
        max_distance=0.3,  # 30cm
        threshold_distance=25,  # 25cm
        min_distance=2  # 2cm
    )

    try:
        print("초음파 센서 테스트 시작 (Ctrl+C로 종료)")
        print("거리 제한: 2cm ~ 30cm")
        
        while True:
            # 평균 거리 측정 (노이즈 감소를 위해)
            distance = sensor.get_average_distance(samples=3, interval=0.1)
            
            if distance is not None:
                print(f"거리: {distance:.1f}cm", end="")
                
                if distance <= sensor.threshold_distance:
                    print(" - 물체 감지!")
                else:
                    print(" - 물체 없음")
            else:
                print("측정 실패 (너무 가깝거나 오류 발생)")
            
            time.sleep(0.5)  # 0.5초 간격으로 측정
            
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    finally:
        sensor.cleanup()

if __name__ == "__main__":
    main()