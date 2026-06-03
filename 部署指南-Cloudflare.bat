@echo off
chcp 65001 >nul 2>&1
title AI手办平台-Cloudflare部署指南

cd /d "%~dp0"

echo ========================================
echo   AI手办平台 - Cloudflare部署指南
echo ========================================
echo.
echo 域名: platform.JasonLee0712.com
echo 本地服务: http://localhost:5000
echo.
echo ========================================
echo   部署步骤
echo ========================================
echo.
echo [步骤1] 登录Cloudflare账号
echo ----------------------------------------
echo 请在终端执行以下命令，会打开浏览器登录:
echo.
echo   cloudflared.exe tunnel login
echo.
echo 登录后会自动生成证书文件。
echo.
pause

echo [步骤2] 创建Tunnel
echo ----------------------------------------
echo 执行以下命令创建Tunnel:
echo.
echo   cloudflared.exe tunnel create ai-3d-platform
echo.
echo 执行后会显示Tunnel ID，请记录下来。
echo 例如: Tunnel ID: 12345678-1234-1234-1234-123456789abc
echo.
pause

echo [步骤3] 配置DNS路由
echo ----------------------------------------
echo 执行以下命令将域名指向Tunnel:
echo.
echo   cloudflared.exe tunnel route dns ai-3d-platform platform.JasonLee0712.com
echo.
echo 这会自动在Cloudflare DNS中添加CNAME记录。
echo.
pause

echo [步骤4] 更新配置文件
echo ----------------------------------------
echo 请打开 cloudflared-config.yml 文件，
echo 将 <TUNNEL_ID> 替换为步骤2中获取的Tunnel ID。
echo.
echo 例如:
echo   tunnel: 12345678-1234-1234-1234-123456789abc
echo   credentials-file: C:\Users\ZhuanZ\.cloudflared\12345678-1234-1234-1234-123456789abc.json
echo.
pause

echo [步骤5] 启动服务
echo --------------------------------echo 1. 先启动本地服务: 双击 "启动AI手办平台.bat"
echo 2. 再启动隧道: 双击 "启动Cloudflare隧道.bat"
echo.
echo 或者使用一键启动脚本: "启动公网访问-Cloudflare.bat"
echo.
pause

echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 访问地址:
echo   - 主站: https://platform.JasonLee0712.com
echo.
echo 后台管理: https://platform.JasonLee0712.com/admin.html
echo 默认账号: admin / admin123
echo.
pause