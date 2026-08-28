# app/analyzer.py
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from typing import List
from app.config import settings


class STLAnalyzer:
    # 周期扫描候选（从短到长）。
    # 服务端自动从中选取 strength 最高的作为真实周期，覆盖客户端传入的 period，
    # 使"每个数据集的周期时长可以不同"。数据量不足某候选 period*2 时跳过该候选。
    PERIOD_CANDIDATES = [3, 5, 7, 14, 30]

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
    def _clean_component(arr: np.ndarray) -> np.ndarray:
        """STL 卷积滤波在序列边界产生 NaN，前向+后向填充避免预测起点丢失。

        ffill 用最后一个有效值填充尾部 NaN（保证 trend[-1] 有效，预测起点合理），
        bfill 填头部 NaN。若全 NaN 则退化为 0。
        """
        if len(arr) == 0:
            return arr
        return pd.Series(arr).ffill().bfill().fillna(0.0).values

    @staticmethod
    def analyze(data: List[float], period: int = 7, forecast_days: int = 30) -> dict:
        n = len(data)

        # ── 周期扫描选优：遍历候选周期，取 strength 最高的作为真实周期 ──
        best_period = None
        best_strength = -1.0
        best_trend = None
        best_seasonal = None

        for cand in STLAnalyzer.PERIOD_CANDIDATES:
            # 数据量不足该候选 period*2 时跳过（STL 至少需要 2 个完整周期）
            if n < cand * 2:
                continue
            try:
                series = pd.Series(data)
                res = STL(series, period=cand, robust=True).fit()
                # 边界 NaN 前向+后向填充，避免 last_trend / seasonal_pattern 取到 NaN
                trend_c = STLAnalyzer._clean_component(res.trend.values)
                seasonal_c = STLAnalyzer._clean_component(res.seasonal.values)
                s = STLAnalyzer.calculate_period_strength(seasonal_c, cand)
                if s > best_strength:
                    best_strength = s
                    best_period = cand
                    best_trend = trend_c
                    best_seasonal = seasonal_c
            except Exception:
                # 该候选分解失败，跳过尝试下一个
                continue

        # 所有候选都因数据不足或分解失败跑不了 → 用客户端传入的 period 兜底
        if best_trend is None:
            if n < period * 2:
                return {
                    "error": "数据量不足，请提供至少 " + str(period * 2) + " 个数据点",
                    "period": period,
                    "strength": 0.0,
                    "forecast": []
                }
            try:
                series = pd.Series(data)
                res = STL(series, period=period, robust=True).fit()
                best_trend = STLAnalyzer._clean_component(res.trend.values)
                best_seasonal = STLAnalyzer._clean_component(res.seasonal.values)
                best_period = period
                best_strength = STLAnalyzer.calculate_period_strength(best_seasonal, period)
            except Exception as e:
                return {
                    "error": "STL 分解失败: " + str(e),
                    "period": period,
                    "strength": 0.0,
                    "forecast": []
                }

        # 使用最优周期做后续分析（period 回填检测值，客户端据此画周期分割）
        period = best_period
        trend = best_trend
        seasonal = best_seasonal
        strength = best_strength

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
            label, mode, msg = "high", "stl", "周期性强（自动检测周期=" + str(period) + "），使用 STL 季节预测"
        elif strength > settings.STRENGTH_THRESHOLD_MEDIUM:
            label, mode, msg = "medium", "hybrid", "周期性中等（自动检测周期=" + str(period) + "），混合季节 + 趋势预测"
        else:
            label, mode, msg = "low", "trend_only", "周期性弱，仅使用趋势预测"

        last_trend = float(trend[-1]) if len(trend) > 0 else 0.0

        if mode == "stl":
            forecast_result = [last_trend + seasonal_pattern[i % period] for i in range(forecast_days)]
        elif mode == "hybrid":
            forecast_result = [last_trend + seasonal_pattern[i % period] * 0.6 for i in range(forecast_days)]
        else:
            trend_slope = float(np.polyfit(range(len(trend)), trend, 1)[0])
            forecast_result = [last_trend + trend_slope * (i + 1) for i in range(forecast_days)]

        # 最终兜底：确保所有预测值为有限 float，避免 NaN 进 JSON 导致 500
        forecast_result = [round(float(np.nan_to_num(v, nan=last_trend)), 2) for v in forecast_result]

        return {
            "period": period,
            "strength": round(float(strength), 3),
            "strength_label": label,
            "seasonal_pattern": seasonal_pattern,
            "trend_last": last_trend,
            "forecast": forecast_result,
            "mode": mode,
            "message": msg,
            "component_count": len(trend)
        }
