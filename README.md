
# CaraneSTL - STL 周期预测服务

基于 STL（Seasonal-Trend decomposition using Loess）分解的周期强度分析和预测服务。

## 功能

- **周期强度分析**：计算时间序列数据的周期性强弱
- **趋势分解**：分离趋势分量和季节性分量
- **智能预测**：根据周期强度自动选择预测策略
  - 周期性强：使用 STL 季节预测
  - 周期性中等：混合季节 + 趋势预测
  - 周期性弱：仅使用趋势预测

## 技术栈

- **FastAPI** - Web 框架
- **statsmodels** - STL 分解算法
- **pandas / numpy** - 数据处理
- **Docker** - 容器化部署

## 快速开始

### Docker 部署（推荐）

`ash
# 构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f
`

### 本地运行

`ash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
`

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| /docs | GET | API 文档（Swagger UI） |
| /health | GET | 健康检查 |
| /analyze | POST | 周期分析与预测 |

### 示例请求

`ash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"data":[5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6],"period":4,"forecast_days":10}'
`

### 示例响应

`json
{
  "period": 4,
  "strength": 1.0,
  "strength_label": "high",
  "seasonal_pattern": [-1.5, -0.5, 0.5, 1.5],
  "trend_last": 6.5,
  "forecast": [5.0, 6.0, 7.0, 8.0, 5.0, 6.0, 7.0, 8.0, 5.0, 6.0],
  "mode": "stl",
  "message": "周期性强，使用 STL 季节预测"
}
`

## 访问地址

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- 分析接口：http://localhost:8000/analyze

## 项目结构

`
CaraneSTL/
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI 应用入口
│   ├── analyzer.py    # STL 分析核心逻辑
│   ├── models.py      # Pydantic 数据模型
│   └── config.py      # 配置
├── tests/
│   └── test_analyzer.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .gitignore
`

## License

MIT
