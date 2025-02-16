from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# 요청 본문을 위한 Pydantic 모델
class HealthDataRequest(BaseModel):
    data_type: str
    amount: float
    duration: float | None = None

@router.post("/health")
async def health_data(request: HealthDataRequest):
    """
    건강 데이터를 처리하는 엔드포인트
    """
    try:
        payload = {
            "serial_number": "SN1",
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": request.data_type,
            "data": {}
        }

        if request.data_type == "feeding":
            payload["data"] = {"amount": request.amount}
        
        elif request.data_type == "intake":
            if request.duration is None:
                raise HTTPException(status_code=400, detail="Duration is required for intake data")
            payload["data"] = {
                "amount": request.amount,
                "duration": request.duration
            }
        
        else:
            raise HTTPException(status_code=400, detail="Invalid data type")

        return payload

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))