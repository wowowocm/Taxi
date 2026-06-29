# -*- coding: utf-8 -*-
"""
生成《局域网访问功能实现技术文档》PDF
使用 fpdf2 库 + Windows 系统中文字体
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF
from datetime import date

# ================================================================
# 中文字体查找
# ================================================================
def find_chinese_font():
    """查找可用的中文字体文件路径 (优先 .ttf 避免 TTC 兼容问题)"""
    candidates = [
        "C:/Windows/Fonts/simhei.ttf",     # 黑体 (首选, 独立TTF)
        "C:/Windows/Fonts/simkai.ttf",     # 楷体
        "C:/Windows/Fonts/simfang.ttf",    # 仿宋
        "C:/Windows/Fonts/STXIHEI.TTF",    # 华文细黑
        "C:/Windows/Fonts/simsunb.ttf",    # 宋体 Bold
        "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑 (TTC-备选)
    ]
    for fp in candidates:
        if os.path.isfile(fp):
            return fp
    raise FileNotFoundError("未找到中文字体")


class ChinesePDF(FPDF):
    """封装中文字体支持"""

    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.font_path = find_chinese_font()
        self.add_font('CN', '', self.font_path)
        self.add_font('CN', 'B', self.font_path)
        self.set_auto_page_break(True, 20)

        # 配色
        self.COLOR_TITLE   = (26, 35, 126)    # 深蓝
        self.COLOR_SUBTITLE = (40, 53, 147)    # 中蓝
        self.COLOR_CODE_BG = (245, 245, 250)   # 淡蓝灰
        self.COLOR_TEXT     = (33, 33, 33)     # 深灰
        self.COLOR_ACCENT   = (0, 131, 143)    # 青
        self.COLOR_WARN     = (230, 81, 0)     # 橙红
        self.COLOR_GREEN    = (0, 150, 0)      # 绿

    # ----------------------------------------------------------
    def title_page(self):
        """封面"""
        self.add_page()
        self.ln(50)
        self.set_font('CN', 'B', 32)
        self.set_text_color(*self.COLOR_TITLE)
        self.cell(0, 14, '局域网访问功能', align='C')
        self.ln(16)
        self.cell(0, 14, '实现技术文档', align='C')
        self.ln(20)

        # 分隔线
        self.set_draw_color(*self.COLOR_ACCENT)
        self.set_line_width(0.6)
        w = 120
        x = (210 - w) / 2
        self.line(x, self.get_y(), x + w, self.get_y())
        self.ln(16)

        self.set_font('CN', '', 14)
        self.set_text_color(*self.COLOR_SUBTITLE)
        self.cell(0, 10, '深圳市出租车出行数据分析系统', align='C')
        self.ln(12)
        self.set_font('CN', '', 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f'文档版本: 1.0  |  日期: {date.today().isoformat()}', align='C')
        self.ln(8)
        self.cell(0, 8, '技术栈: Python Flask + Windows 防火墙 + 网络诊断', align='C')
        self.ln(40)

        self.set_font('CN', '', 10)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, '本文档详细阐述了从一个仅限本机 localhost 访问的 Flask 项目', align='C')
        self.ln(7)
        self.cell(0, 8, '改造为同一局域网内任意设备均可访问的完整技术方案', align='C')
        self.ln(7)
        self.cell(0, 8, '涵盖网络原理、代码实现、防火墙配置、虚拟网卡过滤及 AP 隔离诊断', align='C')

    # ----------------------------------------------------------
    def chapter_title(self, num, title):
        """章标题"""
        self.ln(6)
        self.set_font('CN', 'B', 18)
        self.set_text_color(*self.COLOR_TITLE)
        self.cell(0, 10, f'{num}  {title}')
        self.ln(12)
        # 下划线
        self.set_draw_color(*self.COLOR_ACCENT)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def section_title(self, title):
        """节标题"""
        self.set_font('CN', 'B', 13)
        self.set_text_color(*self.COLOR_SUBTITLE)
        self.set_x(self.l_margin)
        self.cell(0, 8, title)
        self.ln(10)

    def sub_title(self, title):
        """小标题"""
        self.set_font('CN', 'B', 11)
        self.set_text_color(*self.COLOR_ACCENT)
        self.set_x(self.l_margin)
        self.cell(0, 7, f'  {title}')
        self.ln(9)

    def body(self, text):
        """正文"""
        self.set_font('CN', '', 10)
        self.set_text_color(*self.COLOR_TEXT)
        self.set_x(self.l_margin)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet(self, text, indent=8):
        """项目符号"""
        self.set_font('CN', '', 10)
        self.set_text_color(*self.COLOR_TEXT)
        self.set_x(self.l_margin)
        self.cell(indent, 6, '')
        self.cell(5, 6, '>')
        self.multi_cell(170, 6, text)

    def code_block(self, code_text):
        """代码块"""
        self.ln(2)
        y_before = self.get_y()
        self.set_font('CN', '', 8)
        self.set_fill_color(*self.COLOR_CODE_BG)
        lines = code_text.split('\n')
        line_h = 4.5
        total_h = len(lines) * line_h + 8

        # 检查是否需要分页
        if self.get_y() + total_h > 270:
            self.add_page()

        self.set_x(self.l_margin)
        self.set_draw_color(200, 200, 210)
        self.rect(self.l_margin, self.get_y(), 186, total_h, style='DF')
        self.set_text_color(55, 55, 75)

        y = self.get_y() + 4
        for line in lines:
            self.set_xy(self.l_margin + 4, y)
            self.cell(180, line_h, line)
            y += line_h

        self.set_y(y + 4)
        self.set_x(self.l_margin)
        self.ln(3)

    def warn_box(self, text):
        """警告框"""
        self.ln(2)
        self.set_fill_color(255, 245, 230)
        self.set_draw_color(255, 152, 0)
        self.set_text_color(*self.COLOR_WARN)
        self.set_font('CN', 'B', 10)
        y = self.get_y()
        if y + 18 > 270:
            self.add_page()
            y = self.get_y()
        self.rect(12, y, 186, 16, style='DF')
        self.set_xy(16, y + 3)
        self.cell(178, 5, '[!] ' + text)
        self.set_y(y + 20)
        self.set_x(self.l_margin)
        self.ln(2)

    def info_box(self, text):
        """信息框"""
        self.ln(2)
        self.set_fill_color(227, 242, 253)
        self.set_draw_color(33, 150, 243)
        self.set_text_color(1, 87, 155)
        self.set_font('CN', '', 10)
        y = self.get_y()
        if y + 18 > 270:
            self.add_page()
            y = self.get_y()
        self.rect(12, y, 186, 16, style='DF')
        self.set_xy(16, y + 3)
        self.cell(178, 5, '[i] ' + text)
        self.set_y(y + 20)
        self.set_x(self.l_margin)
        self.ln(2)

    def table(self, headers, rows, col_widths=None):
        """简单表格"""
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)

        self.set_x(self.l_margin)
        self.set_font('CN', 'B', 9)
        self.set_fill_color(*self.COLOR_TITLE)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, h, border=1, fill=True, align='C')
        self.ln()

        self.set_font('CN', '', 9)
        self.set_text_color(*self.COLOR_TEXT)
        for row_idx, row in enumerate(rows):
            if row_idx % 2 == 0:
                self.set_fill_color(245, 245, 250)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 7, str(cell), border=1, fill=True, align='C')
            self.ln()
        self.ln(3)


# ================================================================
# 内容构建
# ================================================================
def build_pdf(output_path=None):
    if output_path is None:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(project_dir, 'output', '局域网访问功能实现技术文档.pdf')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pdf = ChinesePDF()
    pdf.set_margin(12)

    # ================================================================
    # 封面
    # ================================================================
    pdf.title_page()

    # ================================================================
    # 第一章: 项目背景与目标
    # ================================================================
    pdf.add_page()
    pdf.chapter_title('一', '项目背景与目标')

    pdf.section_title('1.1 原始状态')
    pdf.body(
        '本项目是一个基于 Python Flask 的 Web 数据可视化系统，包含分析看板（/）和实时运行态势大屏（/realtime）'
        '两个前端页面。开发调试阶段，开发者通过浏览器访问 http://localhost:5000 查看效果，'
        '所有访问仅限本机。'
    )

    pdf.section_title('1.2 需求场景')
    pdf.bullet('团队成员使用各自的笔记本电脑，无需安装 Python 环境即可查看项目')
    pdf.bullet('手机/平板等移动设备快速预览大屏效果')
    pdf.bullet('向客户演示时，大屏可独立运行在一台电脑上，其他人用各自设备观看')
    pdf.bullet('不依赖公网服务器或内网穿透工具（如 ngrok），纯局域网直连')

    pdf.section_title('1.3 最终效果')
    pdf.body(
        '只需在主机的 Windows 防火墙上放行 Flask 端口，同一局域网（包括手机热点）内的任意设备即可'
        '通过浏览器访问主机的局域网 IP 地址（如 http://10.220.79.99:5000）打开完整 Web 项目。'
    )

    # ================================================================
    # 第二章: 网络原理
    # ================================================================
    pdf.add_page()
    pdf.chapter_title('二', '网络原理深度解析')

    pdf.section_title('2.1 IP 地址与网卡绑定')
    pdf.body(
        '一台计算机可能同时拥有多个 IP 地址，每个 IP 绑定在不同的网络接口（网卡）上。'
        'Flask 的监听地址决定了哪些 IP 上的请求会被接收。'
    )

    pdf.sub_title('127.0.0.1（localhost）— 仅本机回环')
    pdf.body(
        '127.0.0.1 是操作系统内置的虚拟回环网卡地址。当 Flask 绑定到 127.0.0.1 时，'
        '只有本机发出的请求能到达 Flask，局域网其他设备发送到主机真实 IP 的数据包会被操作系统直接丢弃。'
    )

    pdf.sub_title('0.0.0.0（INADDR_ANY）— 所有网卡')
    pdf.body(
        '0.0.0.0 是一个特殊的通配地址，表示"监听本机所有网络接口"。当 Flask 绑定到 0.0.0.0 时，'
        '操作系统会将发往 127.0.0.1、局域网真实 IP 以及其他任何网卡 IP 的 5000 端口请求全部转发给 Flask。'
        '这是实现局域网访问的基础前提。'
    )

    pdf.section_title('2.2 数据包在局域网中的旅程')
    pdf.body(
        '以下是一次完整的局域网访问流程，以另一台电脑访问 http://10.220.79.99:5000/ 为例：'
    )
    pdf.bullet('步骤 1 — DNS 解析: 浏览器从 URL 中提取 IP 地址 10.220.79.99（无需 DNS）')
    pdf.bullet('步骤 2 — ARP 广播: 操作系统发送 ARP 请求 "谁是 10.220.79.99?" 到局域网')
    pdf.bullet('步骤 3 — MAC 地址获取: 宿主机网卡回复 "是我，MAC 地址是 XX:XX:XX:XX"')
    pdf.bullet('步骤 4 — TCP 三次握手: 客户端向宿主机 MAC 地址的 5000 端口发起 SYN')
    pdf.bullet('步骤 5 — 防火墙检查: Windows 防火墙检查入站规则，若有 TCP 5000 Allow 则放行')
    pdf.bullet('步骤 6 — Flask 接收: 内核将数据包交给监听 0.0.0.0:5000 的 Flask 进程')
    pdf.bullet('步骤 7 — HTTP 响应: Flask 处理请求 → 返回 HTML → 原路返回给客户端')

    pdf.info_box(
        '整个过程中，Flask 本身无需做任何额外配置——只要 host="0.0.0.0" 且防火墙放行，'
        '操作系统内核会自动处理所有的网络层路由。'
    )

    pdf.section_title('2.3 手机热点的特殊网络拓扑')
    pdf.body(
        '使用手机热点组网时，手机充当了"路由器 + DHCP 服务器"的角色。'
        '连接到同一热点的设备会被分配到同一子网的 IP 地址（如 10.220.79.0/24）。'
        '多数手机热点默认会分配 C 类私网地址（192.168.x.x），部分安卓手机使用 A 类私网（10.x.x.x）。'
    )
    pdf.body(
        '小米手机（如 Xiaomi 14）的热点通常分配 10.x.x.x 网段的地址，这是 RFC 1918 定义的合法私有地址段，'
        '与 192.168.x.x 在功能上完全等价。'
    )

    # ================================================================
    # 第三章: 代码实现
    # ================================================================
    pdf.add_page()
    pdf.chapter_title('三', '代码实现详解')

    pdf.section_title('3.1 Flask 配置 — 监听所有接口')
    pdf.body('src/config.py 中的关键配置项：')
    pdf.code_block(
        'FLASK_HOST = "0.0.0.0"    # 监听本机所有网络接口\n'
        'FLASK_PORT = 5000         # HTTP 服务端口\n'
        'FLASK_DEBUG = True        # 开发模式 (生产环境应设为 False)'
    )
    pdf.body(
        '这是实现局域网访问的唯二前提条件之一。但仅有这个配置还不够——'
        '如果 Windows 防火墙拦截了 5000 端口的入站请求，外部设备依然无法连接。'
    )

    pdf.section_title('3.2 IP 自动检测 — 排除虚拟网卡')
    pdf.body(
        '本机可能同时存在多个 IP 地址（WiFi 网卡、VMware 虚拟网卡、VPN 虚拟网卡、'
        'Radmin 虚拟网卡等）。如果错误地将 VMware 的 192.168.116.1 显示为局域网地址，'
        '其他设备永远无法通过该 IP 访问到本机——因为该 IP 仅存在于虚拟网络中。'
    )

    pdf.sub_title('方案对比')
    pdf.table(
        ['方案', '准确性', '复杂度', '跨平台', '说明'],
        [
            ['socket.gethostname()',  'X 差',  '低', 'V', '无法区分虚拟/真实网卡'],
            ['ipconfig 文本解析',     '~ 一般', '中', 'X', 'GBK 编码不稳定'],
            ['PowerShell Get-NetIPAddress', 'V 好', '中', 'X', '结构化数据 + 适配器名称'],
            ['UDP connect 探测',      'V 好',  '低', 'V', '获取实际出口 IP'],
        ],
        [40, 25, 25, 25, 65]
    )

    pdf.sub_title('最终方案: PowerShell + UDP 组合')
    pdf.code_block(
        'def _get_lan_ip():\n'
        '    """获取本机局域网 IPv4 地址 (自动排除虚拟网卡)"""\n'
        '    \n'
        '    # 虚拟网卡关键词黑名单\n'
        '    VIRTUAL_KEYWORDS = [\n'
        '        "vmware", "virtualbox", "hyper-v", "vethernet",\n'
        '        "wsl", "virtual", "tap-", "radmin", "vpn",\n'
        '        "loopback", "bluetooth", "teredo", "tunnel",\n'
        '    ]\n'
        '    \n'
        '    # Windows: PowerShell 获取适配器名称 + IP\n'
        '    ps_cmd = (\n'
        '        "Get-NetIPAddress -AddressFamily IPv4 | "\n'
        '        "Select-Object IPAddress, InterfaceAlias | "\n'
        '        "ConvertTo-Csv -NoTypeInformation"\n'
        '    )\n'
        '    result = subprocess.run(\n'
        '        ["powershell", "-NoProfile", "-Command", ps_cmd],\n'
        '        capture_output=True, text=True, encoding="utf-8"\n'
        '    )\n'
        '    \n'
        '    for line in result.stdout.split("\\n"):\n'
        '        ip, alias = parse_csv_line(line)\n'
        '        # 检查适配器名称是否包含虚拟关键词\n'
        '        is_virtual = any(kw in alias.lower()\n'
        '                         for kw in VIRTUAL_KEYWORDS)\n'
        '        if not is_virtual:\n'
        '            ips.append(ip)\n'
        '    \n'
        '    # 备选: UDP connect 获取路由出口 IP\n'
        '    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n'
        '    s.connect(("8.8.8.8", 53))  # Google DNS\n'
        '    real_ip = s.getsockname()[0]\n'
        '    s.close()\n'
        '    return ips'
    )

    pdf.section_title('3.3 启动信息展示')
    pdf.body(
        '在 Flask 启动时，自动调用 _get_lan_ip() 检测本机真实 IP 并打印访问地址，'
        '让用户无需手动查找 IP。启动后的控制台输出效果：'
    )
    pdf.code_block(
        '============================================================\n'
        '  城市出行数据分析系统 - Flask Web 服务\n'
        '============================================================\n'
        '\n'
        '  [Access]\n'
        '  ├─ 本机访问: http://localhost:5000\n'
        '  ├─ 分析看板: http://localhost:5000/\n'
        '  └─ 实时大屏: http://localhost:5000/realtime\n'
        '\n'
        '  [LAN] 局域网访问 (同局域网设备):\n'
        '  ├─ http://10.220.79.99:5000/        (分析看板)\n'
        '  └─ http://10.220.79.99:5000/realtime (实时大屏)'
    )

    # ================================================================
    # 第四章: 防火墙配置
    # ================================================================
    pdf.add_page()
    pdf.chapter_title('四', '操作系统防火墙配置')

    pdf.section_title('4.1 为什么防火墙是最大障碍')
    pdf.body(
        'Windows Defender 防火墙默认阻止所有入站连接（除非匹配已有允许规则）。'
        'Flask 绑定 0.0.0.0 只解决了"服务端监听"的问题，防火墙则决定了"客户端能否到达服务端"。'
        '这是 99% 的局域网访问失败的根本原因。'
    )

    pdf.sub_title('Windows 防火墙规则要素')
    pdf.table(
        ['参数', '值', '说明'],
        [
            ['名称', 'Taxi Flask Web (5000)', '便于识别和管理'],
            ['方向', 'Inbound (入站)', '外部设备发往本机的请求'],
            ['协议', 'TCP', 'HTTP 基于 TCP 协议'],
            ['本地端口', '5000', 'Flask 监听端口'],
            ['操作', 'Allow (允许)', '放行匹配的流量'],
            ['配置文件', 'Private + Public', '家庭/工作网络 和 公用网络'],
        ],
        [50, 65, 75]
    )

    pdf.section_title('4.2 自动化配置脚本')
    pdf.body('本项目的 setup_firewall.bat 自动完成防火墙配置（需管理员权限）：')
    pdf.code_block(
        '@echo off\n'
        '\n'
        ':: 检查管理员权限\n'
        'net session >nul 2>&1\n'
        'if %errorlevel% neq 0 (\n'
        '    echo [WARN] 需要管理员权限!\n'
        '    pause && exit /b 1\n'
        ')\n'
        '\n'
        ':: 删除旧规则 (如果存在)\n'
        'netsh advfirewall firewall delete rule \\\n'
        '    name="Taxi Flask Web (5000)" 2>nul\n'
        '\n'
        ':: 创建新规则\n'
        'netsh advfirewall firewall add rule \\\n'
        '    name="Taxi Flask Web (5000)" \\\n'
        '    description="Shenzhen Taxi Analysis" \\\n'
        '    dir=in protocol=TCP localport=5000 \\\n'
        '    action=allow profile=private,public\n'
        '\n'
        'echo [OK] 防火墙规则添加成功!'
    )

    pdf.info_box(
        '如果 Windows 防火墙规则正确但依然不通，还需检查第三方安全软件'
        '（如 360、火绒、McAfee）是否拦截了入站连接。'
    )

    pdf.section_title('4.3 Linux 防火墙 (CentOS 7)')
    pdf.code_block(
        '#!/bin/bash\n'
        '# 自适应检测防火墙类型\n'
        'if firewall-cmd --state 2>/dev/null; then\n'
        '    sudo firewall-cmd --permanent --add-port=5000/tcp\n'
        '    sudo firewall-cmd --reload\n'
        'elif ufw status 2>/dev/null; then\n'
        '    sudo ufw allow 5000/tcp\n'
        'else\n'
        '    sudo iptables -I INPUT -p tcp --dport 5000 -j ACCEPT\n'
        'fi'
    )

    # ================================================================
    # 第五章: 诊断与排错
    # ================================================================
    pdf.add_page()
    pdf.chapter_title('五', '诊断工具与排错指南')

    pdf.section_title('5.1 一键诊断脚本')
    pdf.body(
        '本项目的 diagnose_network.bat 提供了 4 步自动化诊断，'
        '覆盖了局域网访问失败的全部可能原因：'
    )
    pdf.table(
        ['步骤', '检查项', '工具/命令', '可能的失败原因'],
        [
            ['Step 1', 'IP 地址正确性', 'PowerShell Get-NetIPAddress', '虚拟网卡 IP 混淆 → 排除 VMware/VPN'],
            ['Step 2', '端口监听状态', 'netstat -ano | findstr :5000', 'Flask 未启动或绑定 127.0.0.1'],
            ['Step 3', '防火墙规则', 'netsh advfirewall show rule', '规则不存在或被禁用'],
            ['Step 4', 'AP 隔离检查', '提示用户检查手机设置', '手机热点阻止设备间通信'],
        ],
        [28, 35, 62, 65]
    )

    pdf.section_title('5.2 排错清单 (Checklist)')
    checklist_items = [
        ('① Flask 绑定地址', '确认 src/config.py 中 FLASK_HOST = "0.0.0.0" (不是 "127.0.0.1")'),
        ('② 防火墙规则', '以管理员身份运行 setup_firewall.bat'),
        ('③ 端口监听', 'netstat -ano | findstr ":5000 LISTENING" 应有输出'),
        ('④ IP 正确性', 'diagnose_network.bat 输出的 [真实] IP 是否为你网络的实际 IP'),
        ('⑤ 同网段', '其他设备和宿主机必须在同一子网 (检查 IP 前缀是否相同)'),
        ('⑥ AP 隔离', '手机热点设置中确认 "允许设备互联" 已开启或 "AP 隔离" 已关闭'),
        ('⑦ 三方防火墙', '暂时禁用 360/火绒/卡巴斯基 等安全软件测试'),
        ('⑧ Ping 测试', '从另一设备 ping 宿主机 IP，确认基本网络连通性'),
        ('⑨ 浏览器访问', '在另一设备浏览器输入 http://宿主机IP:5000/api/health'),
    ]
    for title, desc in checklist_items:
        pdf.sub_title(title)
        pdf.body(f'  → {desc}')

    pdf.section_title('5.3 AP 隔离：最隐蔽的障碍')
    pdf.warn_box('AP 隔离（客户端隔离）是手机热点最常见的"局域网访问拦截器"！')
    pdf.body(
        'AP 隔离（Access Point Isolation，也叫 Client Isolation）是 Wi-Fi 热点的一项安全功能。'
        '开启后，连接到同一热点的设备之间被逻辑隔离，每个设备只能与热点（即手机）通信，'
        '无法与其他设备直接交互。这原本是为了公共 Wi-Fi 安全设计的，但会阻碍局域网互访。'
    )
    pdf.body('小米/Redmi 手机检查路径：')
    pdf.bullet('设置 → 个人热点 → 查看是否有"允许设备互联"开关')
    pdf.bullet('或 设置 → 连接与共享 → 个人热点 → 更多设置')
    pdf.bullet('如果找不到该选项，尝试更换热点名称后重新连接')

    pdf.body('其他品牌手机：')
    pdf.bullet('iPhone: 个人热点默认无 AP 隔离，通常不需要额外设置')
    pdf.bullet('华为/荣耀: 设置 → 移动网络 → 个人热点 → 更多 → 允许设备互联')
    pdf.bullet('OPPO/vivo: 设置 → 连接与共享 → 个人热点 → AP 频段/管理')

    # ================================================================
    # 第六章: 项目文件清单
    # ================================================================
    pdf.add_page()
    pdf.chapter_title('六', '相关文件与资源')

    pdf.body('以下是与局域网访问功能相关的所有文件及其作用：')
    pdf.table(
        ['文件', '类型', '作用'],
        [
            ['src/config.py', '配置', 'FLASK_HOST="0.0.0.0" — 监听所有网络接口'],
            ['src/web_app.py', '核心代码', '_get_lan_ip() — 智能 IP 检测 + 启动提示'],
            ['main.py', '核心代码', '_get_lan_ips() — 命令行模式 LAN IP 显示'],
            ['setup_firewall.bat', '工具脚本', 'Windows 防火墙一键放行 5000 端口'],
            ['setup_firewall.sh', '工具脚本', 'Linux 防火墙适配 (firewalld/ufw/iptables)'],
            ['diagnose_network.bat', '诊断工具', '4 步自动化网络诊断 + 自动修复'],
        ],
        [55, 25, 110]
    )

    pdf.section_title('6.1 项目完整启动流程')
    pdf.code_block(
        '# ===== 第一步: 配置防火墙 (首次，需管理员) =====\n'
        '右键 setup_firewall.bat → 以管理员身份运行\n'
        '\n'
        '# ===== 第二步: 启动 Flask 项目 =====\n'
        '.venv_py38\\Scripts\\activate\n'
        'python main.py --web\n'
        '\n'
        '# ===== 第三步: 查看控制台输出的 LAN 地址 =====\n'
        '# 会显示类似:\n'
        '#   [LAN] 局域网访问 (同局域网设备):\n'
        '#   ├─ http://10.220.79.99:5000/\n'
        '#   └─ http://10.220.79.99:5000/realtime\n'
        '\n'
        '# ===== 第四步: 其他设备浏览器访问 =====\n'
        '# 手机/平板/其他电脑打开浏览器\n'
        '# 输入 http://10.220.79.99:5000/'
    )

    pdf.section_title('6.2 如果还是不通')
    pdf.code_block(
        '# 运行诊断脚本 (管理员权限)\n'
        '右键 diagnose_network.bat → 以管理员身份运行\n'
        '\n'
        '# 根据输出的 [OK]/[FAIL] 状态定位问题\n'
        '# 最常见的三个原因:\n'
        '#   1. 防火墙未放行 → 脚本自动修复\n'
        '#   2. AP 隔离 → 手动修改手机设置\n'
        '#   3. IP 错误 (虚拟网卡) → 脚本自动显示正确 IP'
    )

    # ================================================================
    # 附录
    # ================================================================
    pdf.add_page()
    pdf.chapter_title('附录', '网络基础概念速查')

    pdf.section_title('RFC 1918 私有地址段')
    pdf.body('以下三个地址段被 IANA 保留用于私有网络，在公网不可路由：')
    pdf.table(
        ['地址范围', 'CIDR', '子网掩码', '可用主机数', '常见场景'],
        [
            ['10.0.0.0 - 10.255.255.255', '10.0.0.0/8', '255.0.0.0', '16,777,214', '企业内网/手机热点'],
            ['172.16.0.0 - 172.31.255.255', '172.16.0.0/12', '255.240.0.0', '1,048,574', '中型企业'],
            ['192.168.0.0 - 192.168.255.255', '192.168.0.0/16', '255.255.0.0', '65,534', '家庭路由器'],
        ],
        [52, 38, 38, 30, 32]
    )

    pdf.section_title('OSI 七层模型视角下的局域网访问')
    pdf.table(
        ['层级', '名称', '本项目的对应操作'],
        [
            ['L7', '应用层', 'HTTP 请求 → Flask 路由 → Jinja2 渲染 HTML'],
            ['L6', '表示层', 'UTF-8 文本 → JSON 序列化/反序列化'],
            ['L5', '会话层', 'TCP 连接管理 (三次握手/四次挥手)'],
            ['L4', '传输层', 'TCP 端口 5000 → 进程 PID 绑定'],
            ['L3', '网络层', 'IP 路由 (0.0.0.0 → 局域网 IP 转发)'],
            ['L2', '数据链路层', 'ARP 解析 MAC 地址 → 以太网帧传输'],
            ['L1', '物理层', 'Wi-Fi 无线电波 / 以太网双绞线'],
        ],
        [18, 30, 142]
    )

    pdf.section_title('关键命令速查表')
    pdf.table(
        ['命令', '用途', '示例输出'],
        [
            ['netstat -ano | findstr :5000', '查看端口监听', 'TCP 0.0.0.0:5000 LISTENING'],
            ['netsh advfirewall firewall show rule', '查看防火墙规则', '规则名称/端口/操作'],
            ['ipconfig', '查看所有IP', 'IPv4 地址列表 + 适配器名'],
            ['ping <对方IP>', '测试连通性', 'Reply from ... time<1ms'],
            ['curl http://IP:5000/api/health', '测试HTTP', '{"status":"ok"}'],
        ],
        [60, 55, 75]
    )

    # ================================================================
    # 保存
    # ================================================================
    pdf.output(output_path)
    return output_path


if __name__ == '__main__':
    path = build_pdf()
    print(f'PDF 已生成: {path}')
    print(f'文件大小: {os.path.getsize(path) / 1024:.1f} KB')
