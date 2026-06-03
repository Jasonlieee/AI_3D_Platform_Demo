@echo off
chcp 65001 >nul 2>&1
title AI手办多模态设计平台

REM 切换到脚本所在目录
cd /d "%~dp0"

echo ========================================
echo   AI手办多模态设计平台
echo ========================================
echo.
echo [INFO] 当前目录: %cd%
echo.
echo [INFO] 正在检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到Python，请先安装Python 3.8+
    echo [INFO] 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python环境正常
echo.
echo [INFO] 正在检查依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [INFO] 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)
echo [OK] 依赖检查完成
echo.
echo [INFO] 正在检查app.py是否存在...
if not exist "app.py" (
    echo [ERROR] 未找到app.py文件
    echo [INFO] 请确保在正确的项目目录中运行此脚本
    pause
    exit /b 1
)
echo [OK] app.py文件存在
echo.
echo [INFO] 正在启动服务...
echo [INFO] 访问地址: http://127.0.0.1:5000
echo [INFO] 后台管理: http://127.0.0.1:5000/admin.html
echo.
echo [提示] 按 Ctrl+C 停止服务
echo ========================================
echo.

REM 等待服务启动后再打开浏览器
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"
python app.py
pause