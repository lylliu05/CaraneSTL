# app/config.py
class Settings:
    PERIOD_DEFAULT = 7
    STRENGTH_THRESHOLD_HIGH = 0.5
    STRENGTH_THRESHOLD_MEDIUM = 0.3
    FORECAST_DAYS = 30

    # 周期扫描选优配置
    PERIOD_CANDIDATES = [2, 3, 4, 5, 7, 10, 14, 30]
    PERIOD_SCAN_MIN_STRENGTH = 0.1

    # 白噪声拒识：随机序列的 strength 基准
    WHITE_NOISE_STRENGTH_THRESHOLD = 0.05

settings = Settings()
