# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import AnalyzeRequest, AnalyzeResponse, HealthResponse
from app.analyzer import STLAnalyzer

app = FastAPI(
    title="STL 周期预测服务",
    description="基于 STL 分解的周期强度分析和预测服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    try:
        result = STLAnalyzer.analyze(
            request.data,
            request.period or 7,
            request.forecast_days or 30
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return AnalyzeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="1.0.0")
