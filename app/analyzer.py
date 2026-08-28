# app/analyzer.py
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from typing import List, Optional, Dict
from app.config import settings

class STLAnalyzer:
    
    @staticmethod
    def calculate_period_strength(seasonal: np.ndarray, period: int) -> float:
        n = len(seasonal)
        if n < period * 2:
            return 0.0
        
        groups = {}
        for i in range(n):
            phase = i % period
            groups.setdefault(phase, []).append(seasonal[i])
        
        overall_mean = np.mean(seasonal)
        between_var = 0
        within_var = 0
        
        for phase, values in groups.items():
            phase_mean = np.mean(values)
            between_var += len(values) * (phase_mean - overall_mean) ** 2
            within_var += np.sum((values - phase_mean) ** 2)
        
        total_var = between_var + within_var
        if total_var == 0:
            return 0.0
        return between_var / total_var

    @staticmethod
    def autocorrelation_at_lag(data: List[float], lag: int) -> float:
        """计算指定滞后阶数的自相关系数"""
        arr = np.array(data, dtype=float)
        n = len(arr)
        if n <= lag or n < 4:
            return 0.0
        mean = arr.mean()
        var = arr.var()
        if var == 0:
            return 0.0
        return np.mean((arr[:-lag] - mean) * (arr[lag:] - mean)) / var

    @staticmethod
    def detect_best_period(
        data: List[float],
        candidates: Optional[List[int]] = None,
        forecast_days: int = 30
    ) -> dict:
        """扫描候选周期，返回 strength 最高的那个结果

        白噪声拒识：对每个候选周期计算 lag-k 自相关系数，
        只接受自相关显著（超出 95% 置信区间）的周期。
        """
        if candidates is None:
            candidates = settings.PERIOD_CANDIDATES

        n = len(data)
        # 白噪声的 95% 置信区间边界
        acf_ci = 1.96 / np.sqrt(n) if n > 0 else 1.0

        best = None
        best_score = -1.0
        best_period = None

        for period in candidates:
            if n < period * 2:
                continue
            try:
                result = STLAnalyzer.analyze(data, period, forecast_days)
                if "error" in result:
                    continue
                # lag-k 自相关检验：必须在 95% 置信区间外才算显著
                lag_k_acf = abs(STLAnalyzer.autocorrelation_at_lag(data, period))
                if lag_k_acf < acf_ci:
                    # 该周期的自相关不显著，跳过
                    continue
                # 综合评分 = STL strength × lag-k 自相关显著性
                score = result["strength"] * (lag_k_acf / acf_ci)
                if score > best_score:
                    best_score = score
                    best = result
                    best_period = period
            except Exception:
                continue

        # 白噪声拒识：所有候选周期的自相关都不显著
        if best is None or best_score < settings.PERIOD_SCAN_MIN_STRENGTH:
            last_val = float(data[-1]) if len(data) > 0 else 0
            try:
                trend_slope = float(np.polyfit(range(len(data)), data, 1)[0])
            except Exception:
                trend_slope = 0.0
            label = "white_noise" if best is None else "low"
            msg = "数据近似白噪声，无显著周期" if best is None else "未检测到显著周期，使用趋势预测"
            return {
                "period": 0,
                "strength": round(best["strength"] if best else 0.0, 3),
                "strength_label": label,
                "seasonal_pattern": [],
                "trend_last": last_val,
                "forecast": [round(last_val + trend_slope * (i + 1), 2) for i in range(forecast_days)],
                "mode": "trend_only",
                "message": msg,
                "component_count": len(data),
                "periods_scanned": candidates,
            }

        best["periods_scanned"] = candidates
        return best
    
    @staticmethod
    def analyze(data: List[float], period: int = 7, forecast_days: int = 30) -> dict:
        if len(data) < period * 2:
            return {"error": "数据量不足，请提供至少 " + str(period * 2) + " 个数据点", "period": period, "strength": 0.0, "forecast": []}
        
        series = pd.Series(data)
        
        try:
            stl = STL(series, period=period, robust=True)
            stl_result = stl.fit()
        except Exception as e:
            return {"error": "STL 分解失败: " + str(e), "period": period, "strength": 0.0, "forecast": []}
        
        trend = stl_result.trend.values
        seasonal = stl_result.seasonal.values
        
        strength = STLAnalyzer.calculate_period_strength(seasonal, period)
        
        seasonal_pattern = []
        for i in range(period):
            phase_values = seasonal[i::period]
            if len(phase_values) > 0:
                seasonal_pattern.append(float(np.mean(phase_values)))
            else:
                seasonal_pattern.append(0.0)
        
        pattern_mean = np.mean(seasonal_pattern)
        seasonal_pattern = [round(v - pattern_mean, 3) for v in seasonal_pattern]
        
        if strength > settings.STRENGTH_THRESHOLD_HIGH:
            label, mode, msg = "high", "stl", "周期性强，使用 STL 季节预测"
        elif strength > settings.STRENGTH_THRESHOLD_MEDIUM:
            label, mode, msg = "medium", "hybrid", "周期性中等，混合季节 + 趋势预测"
        else:
            label, mode, msg = "low", "trend_only", "周期性弱，仅使用趋势预测"
        
        last_trend = float(trend[-1]) if len(trend) > 0 else 0
        
        if mode == "stl":
            forecast_result = [last_trend + seasonal_pattern[i % period] for i in range(forecast_days)]
        elif mode == "hybrid":
            forecast_result = [last_trend + seasonal_pattern[i % period] * 0.6 for i in range(forecast_days)]
        else:
            trend_slope = float(np.polyfit(range(len(trend)), trend, 1)[0])
            forecast_result = [last_trend + trend_slope * (i + 1) for i in range(forecast_days)]
        
        forecast_result = [round(v, 2) for v in forecast_result]
        
        return {
            "period": period,
            "strength": round(strength, 3),
            "strength_label": label,
            "seasonal_pattern": seasonal_pattern,
            "trend_last": float(trend[-1]) if len(trend) > 0 else 0,
            "forecast": forecast_result,
            "mode": mode,
            "message": msg,
            "component_count": len(trend)
        }
