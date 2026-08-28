# tests/test_analyzer.py
import pytest
from app.analyzer import STLAnalyzer

def test_analyze_with_periodic_data():
    data = [5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6]
    result = STLAnalyzer.analyze(data, period=4, forecast_days=10)
    assert result["period"] == 4
    assert result["strength"] > 0.5
    assert len(result["forecast"]) == 10

def test_analyze_with_short_data():
    data = [1,2,3,4]
    result = STLAnalyzer.analyze(data, period=7, forecast_days=10)
    assert "error" in result
