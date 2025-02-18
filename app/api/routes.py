from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ScheduleUpdate(BaseModel):
    schedule: dict

@router.post("/schedule/update")
async def update_schedule(data: ScheduleUpdate):
    try:
        # 스케줄 업데이트 로직
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))