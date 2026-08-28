# app/models.py
from pydantic import BaseModel
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    data: List[float]
    period: Optional[int] = 7
    forecast_days: Optional[int] = 30
    auto_detect: Optional[bool] = True

class AnalyzeResponse(BaseModel):
    period: int
    strength: float
    strength_label: str
    seasonal_pattern: List[float]
    trend_last: float
    forecast: List[float]
    mode: str
    message: str
    periods_scanned: Optional[List[int]] = None

class HealthResponse(BaseModel):
    status: str
    version: str
