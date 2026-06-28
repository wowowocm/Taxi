@echo off
chcp 65001 >nul
echo ============================================================
echo   深圳市出租车出行数据分析系统 — Windows 防火墙配置
echo   开放端口 5000，允许局域网设备访问 Flask Web 服务
echo ============================================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] 需要管理员权限才能配置防火墙!
    echo [INFO] 请右键此文件 → "以管理员身份运行"
    echo.
    echo 或者手动执行以下命令 (管理员 PowerShell):
    echo   New-NetFirewallRule -DisplayName "Taxi Flask Web (5000)" ^
    echo     -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
    echo.
    pause
    exit /b 1
)

echo [INFO] 正在检查现有防火墙规则...
netsh advfirewall firewall show rule name="Taxi Flask Web (5000)" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] 规则已存在，正在删除旧规则...
    netsh advfirewall firewall delete rule name="Taxi Flask Web (5000)"
)

echo [INFO] 正在添加防火墙入站规则 (TCP 5000)...
netsh advfirewall firewall add rule ^
    name="Taxi Flask Web (5000)" ^
    description="深圳出租车数据分析系统 Flask Web 服务" ^
    dir=in ^
    protocol=TCP ^
    localport=5000 ^
    action=allow ^
    profile=private,public

if %errorlevel% equ 0 (
    echo [OK] 防火墙规则添加成功!
    echo.
    echo   规则名称:  Taxi Flask Web (5000)
    echo   端口:      TCP 5000
    echo   方向:      入站 (允许局域网设备访问)
    echo   配置文件:  专用网络 + 公用网络
    echo.
    echo 现在同局域网设备可以通过 http://你的IP:5000 访问项目了!
) else (
    echo [ERROR] 防火墙规则添加失败，请手动配置
)

echo.
pause
