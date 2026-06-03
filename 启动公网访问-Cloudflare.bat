@echo off
chcp 65001 >nul 2>&1
title AI手办平台-公网访问(Cloudflare)

cd /d "%~dp0"

echo ========================================
echo   AI手办平台 - 公网访问 (Cloudflare)
echo ========================================
echo.
echo 域名: https://platform.JasonLee0712.com
echo 本地服务: http://localhost:5000
echo.
echo ========================================
echo.

echo [INFO] 正在检查配置...
if not exist "cloudflared.exe" (
    echo [ERROR] 未找到cloudflared.exe
    pause
    exit /b 1
)

if not exist "app.py" (
    echo [ERROR] 未找到app.py
    pause
    exit /b 1
)

echo [OK] 配置检查完成
echo.

echo [INFO] 正在启动本地服务...
start "AI手办平台-本地服务" cmd /k "cd /d "%~dp0" && python app.py"

echo [INFO] 等待本地服务启动...
timeout /t 3 /nobreak >nul

echo [INFO] 正在启动Cloudflare隧道...
echo.
echo [提示] 按 Ctrl+C 停止隧道
echo ========================================
echo.

cloudflared.exe tunnel run ai-3d-platform

pause