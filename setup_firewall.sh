#!/bin/bash
# ================================================================
#   深圳出租车出行数据分析系统 — Linux 防火墙配置
#   开放端口 5000，允许局域网设备访问 Flask Web 服务
# ================================================================

echo "============================================================"
echo "  深圳出租车出行数据分析系统 — Linux 防火墙配置"
echo "  开放端口 5000，允许局域网设备访问 Flask Web 服务"
echo "============================================================"
echo ""

# 检测使用的防火墙类型
IPTABLES=$(which iptables 2>/dev/null)
FIREWALLD=$(which firewall-cmd 2>/dev/null)
UFW=$(which ufw 2>/dev/null)

if [ -n "$FIREWALLD" ] && systemctl is-active --quiet firewalld 2>/dev/null; then
    echo "[INFO] 检测到 firewalld"
    sudo firewall-cmd --permanent --add-port=5000/tcp
    sudo firewall-cmd --reload
    echo "[OK] firewalld 规则已添加"

elif [ -n "$UFW" ] && ufw status | grep -q "Status: active" 2>/dev/null; then
    echo "[INFO] 检测到 ufw"
    sudo ufw allow 5000/tcp comment "Taxi Flask Web"
    echo "[OK] ufw 规则已添加"

elif [ -n "$IPTABLES" ]; then
    echo "[INFO] 使用 iptables"
    sudo iptables -I INPUT -p tcp --dport 5000 -j ACCEPT
    # 持久化 (CentOS/RHEL)
    if [ -f /etc/sysconfig/iptables ]; then
        sudo service iptables save 2>/dev/null
    fi
    echo "[OK] iptables 规则已添加"

else
    echo "[WARN] 未检测到防火墙，或防火墙未启用"
    echo "[INFO] 端口 5000 可能已默认开放"
fi

echo ""
echo "现在同局域网设备可以通过 http://$(hostname -I | awk '{print $1}'):5000 访问项目了!"
