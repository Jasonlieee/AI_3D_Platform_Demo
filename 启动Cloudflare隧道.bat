@echo off
chcp 65001 >nul 2>&1
title AI手办平台-Cloudflare隧道

cd /d "%~dp0"

echo ========================================
echo   AI手办平台 - Cloudflare Tunnel
echo ========================================
echo.
echo [INFO] 隧道名称: ai-3d-platform
echo [INFO] 域名: platform.JasonLee0712.com
echo [INFO] 本地服务: http://localhost:5000
echo.
echo [步骤1] 检查cloudflared.exe是否存在...
if not exist "cloudflared.exe" (
    echo [ERROR] 未找到cloudflared.exe
    echo [INFO] 请下载: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    pause
    exit /b 1
)
echo [OK] cloudflared.exe存在
echo.
echo [步骤2] 获取Tunnel Token...
for /f "tokens=*" %%i in ('cloudflared.exe tunnel token ai-3d-platform') do set TUNNEL_TOKEN=%%i
if "%TUNNEL_TOKEN%"=="" (
    echo [ERROR] 无法获取Tunnel Token
    echo [INFO] 请确保已登录并创建Tunnel
    pause
    exit /b 1
)
echo [OK] Token获取成功
echo.
echo [步骤3] 启动隧道...
echo [提示] 按 Ctrl+C 停止隧道
echo ========================================
echo.

:: 启动隧道
cloudflared.exe tunnel run --token %TUNNEL_TOKEN%

pause