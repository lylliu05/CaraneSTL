# build.ps1 - STL Prediction Service 构建脚本

param(
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

# 颜色函数
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "[✓] $args" -ForegroundColor Green }
function Write-Error { Write-Host "[✗] $args" -ForegroundColor Red }
function Write-Warning { Write-Host "[!] $args" -ForegroundColor Yellow }
function Write-Step { Write-Host "`n▶ $args" -ForegroundColor Magenta }

# 获取 Python 命令
function Get-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $cmd) { Write-Error "未找到 Python"; exit 1 }
    return $cmd
}

# 清理
function Do-Clean {
    Write-Step "清理缓存..."
    Get-ChildItem -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
    Remove-Item -Recurse -Force ".pytest_cache" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force ".coverage" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "htmlcov" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
    Write-Success "清理完成!"
}

# 安装依赖
function Do-Install {
    Write-Step "安装依赖..."
    $python = Get-Python
    & $python.Source -m pip install --upgrade pip -q
    & $python.Source -m pip install -r requirements.txt
    Write-Success "依赖安装完成!"
}

# 运行测试
function Do-Test {
    Write-Step "运行测试..."
    $python = Get-Python
    & $python.Source -m pytest tests/ -v
    if ($LASTEXITCODE -eq 0) {
        Write-Success "测试通过!"
    } else {
        Write-Error "测试失败!"
        exit 1
    }
}

# 本地运行
function Do-Run {
    Write-Step "启动服务 http://localhost:8000"
    Write-Info "按 Ctrl+C 停止"
    $python = Get-Python
    $env:PYTHONPATH = $PSScriptRoot
    & $python.Source -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Docker 构建
function Do-Docker {
    Write-Step "构建 Docker 镜像..."
    docker build -t stl-prediction-service:latest .
    if ($LASTEXITCODE -eq 0) {
        Write-Success "镜像构建完成!"
    } else {
        Write-Error "Docker 构建失败!"
        exit 1
    }
}

# Docker Compose
function Do-Compose {
    Write-Step "启动 Docker Compose..."
    docker-compose up -d
    Write-Success "服务已启动!"
}

function Do-ComposeStop {
    Write-Step "停止 Docker Compose..."
    docker-compose down
    Write-Success "服务已停止!"
}

# 测试 API
function Do-TestApi {
    Write-Step "测试 API..."
    
    $body = '{"data":[5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6,7,8,5,6],"period":4,"forecast_days":10}'
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/analyze" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body
        
        Write-Info "周期: $($response.period)"
        Write-Info "强度: $($response.strength) ($($response.strength_label))"
        Write-Info "模式: $($response.mode)"
        Write-Info "预测: $($response.forecast -join ', ')"
        Write-Success "API 测试通过!"
    } catch {
        Write-Error "API 测试失败，请确认服务已启动"
        Write-Info "提示: .\build.ps1 -Action run"
    }
}

# 健康检查
function Do-Health {
    Write-Step "健康检查..."
    try {
        $r = Invoke-RestMethod "http://localhost:8000/health"
        Write-Info "状态: $($r.status)"
        Write-Info "版本: $($r.version)"
        Write-Success "服务正常运行!"
    } catch {
        Write-Error "服务未响应"
    }
}

# 打包
function Do-Package {
    Write-Step "打包..."
    if (-not (Test-Path "dist")) { New-Item -ItemType Directory -Path "dist" -Force | Out-Null }
    $name = "stl-service_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
    Compress-Archive -Path "app","tests","requirements.txt","Dockerfile","docker-compose.yml","README.md" -DestinationPath "dist\$name" -Force
    Write-Success "打包完成: dist\$name"
}

# 帮助
function Do-Help {
    Write-Host @"
STL Prediction Service 构建脚本

用法: .\build.ps1 -Action <动作>

动作:
  all       完整构建 (清理 + 安装 + 测试)
  clean     清理缓存
  install   安装依赖
  test      运行测试
  run       本地运行服务
  docker    构建 Docker 镜像
  compose   启动 Docker Compose
  composestop 停止 Docker Compose
  health    健康检查
  testapi   测试 API
  package   打包部署文件
  help      显示帮助

示例:
  .\build.ps1 -Action run
  .\build.ps1 -Action all
"@
}

# ============================================
# 主入口
# ============================================
switch ($Action) {
    "all"        { Do-Clean; Do-Install; Do-Test; Write-Success "`n✅ 构建完成!" }
    "clean"      { Do-Clean }
    "install"    { Do-Install }
    "test"       { Do-Test }
    "run"        { Do-Run }
    "docker"     { Do-Docker }
    "compose"    { Do-Compose }
    "composestop"{ Do-ComposeStop }
    "health"     { Do-Health }
    "testapi"    { Do-TestApi }
    "package"    { Do-Package }
    "help"       { Do-Help }
    default {
        Write-Error "未知动作: $Action"
        Do-Help
        exit 1
    }
}