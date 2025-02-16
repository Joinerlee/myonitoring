from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints

app = FastAPI(
    title="Cat Health Monitor",
    description="Raspberry Pi based cat health monitoring system",
    version="0.1.0"
)

# CORS 설정
origins = [
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터를 /api 프리픽스로 포함
app.include_router(endpoints.router, prefix="/api")

@app.get("/")
async def root():
    return {"status": "running"}