# app/analyzer.py
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from scipy.signal import find_peaks
from typing import List
from app.config import settings


class STLAnalyzer:
    # 周期扫描候选（ACF 降级时使用，从短到长）。
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
        """STL 卷积滤波在序列边界产生 NaN，前向+后向填充避免预测起点丢失。"""
        if len(arr) == 0:
            return arr
        return pd.Series(arr).ffill().bfill().fillna(0.0).values

    @staticmethod
    def detect_period_acf(data: List[float], max_lag: int = 30, threshold: float = 0.3) -> int:
        """ACF 自相关检测主周期（方案C主通道）。

        流程：线性去趋势 → 算各 lag 自相关 → 找 height>=threshold 的峰 → 取最高峰 lag。
        返回检测到的周期长度（任意值，如 10/13/17），无显著周期返回 0。

        - 去趋势：避免上升趋势主导 ACF 测出长周期假峰；
        - threshold=0.3：过滤白噪声的弱峰；
        - 数据 < max_lag*2 时不可靠，返回 0 降级。
        """
        n = len(data)
        if n < max_lag * 2:
            return 0

        arr = np.array(data, dtype=float)
        # 线性去趋势
        x = np.arange(n)
        slope, intercept = np.polyfit(x, arr, 1)
        detrended = arr - (slope * x + intercept)

        # 计算 ACF（Pearson 自相关）
        acf_values = []
        for lag in range(1, min(max_lag, n - 1) + 1):
            y1 = detrended[:-lag]
            y2 = detrended[lag:]
            # 全相同值时 std=0，corrcoef 返回 NaN，记 0
            if y1.std() == 0 or y2.std() == 0:
                acf_values.append(0.0)
                continue
            corr = np.corrcoef(y1, y2)[0, 1]
            acf_values.append(corr if not np.isnan(corr) else 0.0)

        if not acf_values:
            return 0

        # 找峰值（height=threshold 过滤弱峰）
        peaks, properties = find_peaks(acf_values, height=threshold)
        if len(peaks) == 0:
            return 0

        # 取最高峰对应的 lag（+1 因为 lag 从 1 开始）
        highest_idx = peaks[np.argmax(properties['peak_heights'])]
        detected = highest_idx + 1

        if detected < 2 or detected > max_lag:
            return 0
        return int(detected)

    @staticmethod
    def analyze(data: List[float], period: int = 7, forecast_days: int = 30) -> dict:
        n = len(data)

        best_trend = None
        best_seasonal = None
        best_period = None
        best_strength = -1.0
        period_source = ""

        # ── 主通道：ACF 前置周期检测（任意周期）──
        detected = STLAnalyzer.detect_period_acf(data, max_lag=30, threshold=0.3)
        if detected > 0 and n >= detected * 2:
            try:
                series = pd.Series(data)
                res = STL(series, period=detected, robust=True).fit()
                best_trend = STLAnalyzer._clean_component(res.trend.values)
                best_seasonal = STLAnalyzer._clean_component(res.seasonal.values)
                best_period = detected
                best_strength = STLAnalyzer.calculate_period_strength(best_seasonal, detected)
                period_source = "ACF"
            except Exception:
                best_trend = None  # ACF 周期 STL 失败，降级候选扫描

        # ── 降级：候选扫描选优（ACF 无显著峰或 STL 失败时）──
        if best_trend is None:
            for cand in STLAnalyzer.PERIOD_CANDIDATES:
                if n < cand * 2:
                    continue
                try:
                    series = pd.Series(data)
                    res = STL(series, period=cand, robust=True).fit()
                    trend_c = STLAnalyzer._clean_component(res.trend.values)
                    seasonal_c = STLAnalyzer._clean_component(res.seasonal.values)
                    s = STLAnalyzer.calculate_period_strength(seasonal_c, cand)
                    if s > best_strength:
                        best_strength = s
                        best_period = cand
                        best_trend = trend_c
                        best_seasonal = seasonal_c
                        period_source = "scan"
                except Exception:
                    continue

        # ── 兜底：ACF + 候选都失败，用客户端传入的 period ──
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
                period_source = "fallback"
            except Exception as e:
                return {
                    "error": "STL 分解失败: " + str(e),
                    "period": period,
                    "strength": 0.0,
                    "forecast": []
                }

        # 使用检测周期做后续分析
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

        src_tag = "ACF检测" if period_source == "ACF" else ("候选扫描" if period_source == "scan" else "默认")
        if strength > settings.STRENGTH_THRESHOLD_HIGH:
            label, mode, msg = "high", "stl", "周期性强（" + src_tag + "周期=" + str(period) + "），使用 STL 季节预测"
        elif strength > settings.STRENGTH_THRESHOLD_MEDIUM:
            label, mode, msg = "medium", "hybrid", "周期性中等（" + src_tag + "周期=" + str(period) + "），混合季节 + 趋势预测"
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

        # 最终兜底：确保所有预测值为有限 float
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
