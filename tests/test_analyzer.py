# tests/test_analyzer.py
import pytest
import random
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

def test_detect_best_period_finds_real_period():
    # 周期=7 的数据，扫描应检测出周期 7
    data = [10,12,14,16,18,20,22] * 10  # 70 个点，周期 7
    result = STLAnalyzer.detect_best_period(data, forecast_days=14)
    assert result["period"] == 7
    assert result["strength"] > 0.8
    assert "periods_scanned" in result
    assert result["mode"] == "stl"

def test_detect_best_period_with_period4_data():
    # 周期=4 的数据，扫描应检测出周期 4 而非 7
    data = [5,6,7,8] * 10  # 40 个点，周期 4
    result = STLAnalyzer.detect_best_period(data, forecast_days=10)
    assert result["period"] == 4
    assert result["strength"] > 0.8

def test_detect_best_period_white_noise():
    # 随机数据应被识别为白噪声
    random.seed(42)
    data = [random.uniform(1, 100) for _ in range(60)]
    result = STLAnalyzer.detect_best_period(data, forecast_days=10)
    assert result["strength_label"] == "white_noise"
    assert result["mode"] == "trend_only"
    assert len(result["forecast"]) == 10

def test_detect_best_period_insufficient_data():
    # 数据太少，所有候选周期都不满足 period*2
    data = [1,2,3]
    result = STLAnalyzer.detect_best_period(data, forecast_days=5)
    assert "periods_scanned" in result
    assert len(result["forecast"]) == 5
