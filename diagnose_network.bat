@echo off
chcp 65001 >nul
title 局域网连接诊断工具 — Taxi 项目

echo ============================================================
echo   局域网连接诊断工具
echo   深圳出租车出行数据分析系统
echo ============================================================
echo.

echo [Step 1/4] 检查当前 WiFi/热点 IP 地址...
echo.
powershell -NoProfile -Command "
Write-Host '  适配器                     IP地址' -ForegroundColor Cyan
Write-Host '  --------                   -------' -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.IPAddress -notlike '127.*' -and \$_.IPAddress -notlike '169.254.*' } | ForEach-Object {
    \$ip = \$_.IPAddress
    \$name = \$_.InterfaceAlias
    if (\$name -match 'VMware|VirtualBox|Hyper-V|WSL|Radmin|VPN|Tunnel|Loopback|Teredo|vEthernet|TAP') {
        Write-Host ('  [虚拟] ' + \$name.Substring(0,[Math]::Min(30,\$name.Length)) + '  ' + \$ip) -ForegroundColor DarkGray
    } else {
        Write-Host ('  [真实] ' + \$name.Substring(0,[Math]::Min(30,\$name.Length)) + '  ' + \$ip) -ForegroundColor Green
    }
}
"
echo.

echo [Step 2/4] 检查 Flask 端口 5000 监听状态...
echo.
netstat -ano | findstr ":5000.*LISTENING" >nul
if %errorlevel% equ 0 (
    echo   [OK] 端口 5000 正在监听 (0.0.0.0) — 外部可连接
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000.*LISTENING"') do (
        for /f "tokens=1" %%b in ('tasklist /FI "PID eq %%a" ^| findstr "%%a"') do (
            echo   进程: %%b (PID: %%a)
        )
    )
) else (
    echo   [FAIL] 端口 5000 未在监听!
    echo   请先启动项目: python main.py --web
)
echo.

echo [Step 3/4] 检查 Windows 防火墙规则...
echo.
netsh advfirewall firewall show rule name="Taxi Flask Web (5000)" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] 防火墙规则已存在
    netsh advfirewall firewall show rule name="Taxi Flask Web (5000)" | findstr /C:"已启用" /C:"Enabled" /C:"操作" /C:"Action"
) else (
    echo   [FAIL] 防火墙规则不存在!
    echo   需要以管理员身份运行此脚本...
    echo.
    net session >nul 2>&1
    if %errorlevel% neq 0 (
        echo   [WARN] 当前没有管理员权限!
        echo   请右键此文件 "以管理员身份运行"
        goto :end
    )
    echo   [INFO] 正在创建防火墙规则...
    netsh advfirewall firewall add rule name="Taxi Flask Web (5000)" description="Shenzhen Taxi Analysis" dir=in protocol=TCP localport=5000 action=allow profile=private,public >nul
    if %errorlevel% equ 0 (
        echo   [OK] 防火墙规则已创建!
    ) else (
        echo   [ERROR] 防火墙规则创建失败
    )
)
echo.

echo [Step 4/4] 手机热点 AP 隔离检查...
echo.
echo   [INFO] 手机热点可能开启了 "AP 隔离" 功能
echo   AP 隔离会阻止连接到同一热点的设备互相通信!
echo.
echo   请检查你的手机热点设置:
echo   小米手机: 设置 ^> 个人热点 ^> 允许设备互联 / AP隔离
echo   如果看到类似选项，请确保 "允许设备互联" 已打开
echo.

echo ============================================================
echo   诊断完成!
echo ============================================================
echo.
echo   正确的访问地址:
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.IPAddress -notlike '127.*' -and \$_.IPAddress -notlike '169.254.*' -and \$_.InterfaceAlias -notmatch 'VMware|VirtualBox|Hyper-V|Radmin|VPN|Loopback|TAP|vEthernet' } | Select-Object -ExpandProperty IPAddress"') do (
    echo     http://%%a:5000/        (分析看板)
    echo     http://%%a:5000/realtime (实时大屏)
)

:end
echo.
pause
