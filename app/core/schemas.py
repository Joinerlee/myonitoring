from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# 급여 데이터 모델
class FeedingData(BaseModel):
    amount: float

# 섭취 데이터 모델
class IntakeData(BaseModel):
    duration: float
    amount: float

# 눈 상태 데이터 모델
class EyeCondition(BaseModel):
    eye_side: str  # "left" or "right"
    blepharitis_prob: float
    conjunctivitis_prob: float
    corneal_sequestrum_prob: float
    non_ulcerative_keratitis_prob: float
    corneal_ulcer_prob: float

class EyeData(BaseModel):
    eyes: List[EyeCondition]

# 통합 헬스 데이터 모델
class HealthData(BaseModel):
    serial_number: str
    datetime: datetime
    type: str  # "feeding", "intake", or "eye"
    data: dict  # FeedingData | IntakeData | EyeData

# 센서 데이터 모델
class SensorData(BaseModel):
    ultrasonic_distance: float  # 초음파 센서 거리값 (cm)
    infrared_detected: bool     # 적외선 센서 감지 여부

# 모터 제어 모델
class MotorControl(BaseModel):
    speed: int       # 모터 속도 (0-100)
    duration: float  # 동작 시간 (초)
    direction: str   # "forward" or "backward"

# 카메라 설정 모델
class CameraConfig(BaseModel):
    resolution: tuple[int, int] = (640, 480)  # 해상도
    framerate: int = 30                       # 프레임레이트
    format: str = "rgb"                       # 이미지 포맷

# 시스템 설정 모델
class SystemConfig(BaseModel):
    feeding_schedule: List[str]  # 급여 시간 리스트 (HH:MM 형식)
    feeding_amount: float        # 1회 급여량
    sensor_interval: float       # 센서 체크 간격 (초)
    camera_enabled: bool         # 카메라 활성화 여부