@echo off
chcp 65001 >nul 2>&1
title AI手办平台-后台管理
echo ========================================
echo   AI手办平台 - 后台管理
echo ========================================
echo.
echo [INFO] 正在启动服务并打开后台管理页面...
echo [INFO] 后台管理地址: http://127.0.0.1:5000/admin.html
echo.
start "" "http://127.0.0.1:5000/admin.html"
python app.py
pause