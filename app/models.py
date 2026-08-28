# app/models.py
from pydantic import BaseModel
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    data: List[float]
    period: Optional[int] = 7
    forecast_days: Optional[int] = 30

class AnalyzeResponse(BaseModel):
    period: int
    strength: float
    strength_label: str
    seasonal_pattern: List[float]
    trend_last: float
    forecast: List[float]
    mode: str
    message: str

class HealthResponse(BaseModel):
    status: str
    version: str
