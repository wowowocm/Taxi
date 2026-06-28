# 🚕 城市出行数据分析系统 (Urban Travel Analysis System)

基于GPS轨迹数据的深圳市出租车出行行为分析系统

[![Python](https://img.shields.io/badge/Python-3.8%20%7C%203.12-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.2.5-green)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0.13-orange)](https://www.mysql.com/)
[![ECharts](https://img.shields.io/badge/ECharts-5.5.0-aa344d)](https://echarts.apache.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900)](https://leafletjs.com/)
[![License](https://img.shields.io/badge/License-Internal-lightgrey)]()

---

## 📖 项目概述

本项目基于深圳市 **500 辆出租车全天候 GPS 轨迹数据**（约 **160 万条**记录），通过**数据清洗 → 特征工程 → 时空分析 → 可视化呈现 → 实时监控**五层数据价值递进模型，挖掘城市居民出行模式。

### ✨ 亮点

- 🧹 **5 条清洗规则**将 160 万条 GPS 信号压缩为 **8,517 条有效 OD 行程** (188:1)
- 📊 **2 套 Web 看板**: 分析看板 (9 张 ECharts 图表) + 实时大屏 (暗黑科幻风全屏)
- 🗺 **深圳地图 OD 流向图**: GeoJSON + ECharts graph/geo 系列 29 节点 25 条箭头
- 🖥 **实时运行态势大屏**: Leaflet 热力图 + 双 Y 轴趋势 + 排行联动
- 🗄️ **MySQL 数据源**: 3 张表 + 预计算聚合缓存，毫秒级 API 响应
- 🌐 **局域网共享**: 一键防火墙配置，手机/平板/其他电脑可访问
- 📐 **16 种数学知识**: Haversine / DBSCAN / FSM / 插值 / 统计矩 / 矩阵代数…

> 📖 详细开发思想与数学分析请见:  
> - [开发思想与架构文档](log/开发思想.md) — 740 行完整技术文档  
> - [数据清洗的数学思想](log/数据清洗的数学思想.md) — 17 个数学维度剖析

---

## 🏗 项目结构

```
Taxi/
├── main.py                         # 🚪 项目主入口 (CLI: --clean/--web/--report)
├── requirements.txt                # 📦 Python 3.12 依赖清单
├── requirements_py38.txt           # 📦 Python 3.8 依赖清单 (推荐)
├── setup_win.bat                   # 🪟 Windows 一键安装脚本
├── setup_vm.sh                     # 🐧 CentOS 7 部署脚本
├── setup_firewall.bat              # 🔥 Windows 防火墙配置 (局域网访问)
├── setup_firewall.sh               # 🔥 Linux 防火墙配置 (局域网访问)
├── README.md                       # 📖 本文件
├── .gitignore
│
├── src/                            # 💻 源代码
│   ├── config.py                   # ⚙️ 全局配置 (路径/阈值/MySQL/地理范围)
│   ├── logger.py                   # 📝 统一日志模块 (单例 + 日期分片)
│   ├── data_loader.py              # 📥 CSV 加载 + 编码检测 + 质量报告
│   ├── data_cleaner.py             # 🧹 5 条规则清洗流水线
│   │                               #    ①异常坐标 ②速度插值 ③行程切片 ④OD提取 ⑤异常过滤
│   ├── trip_extractor.py           # 🚗 GPS→OD 提取 (Pandas/PySpark 双模式)
│   ├── temporal_analysis.py        # ⏱ 时序分析 (24h 分布/高峰/效率/时长/距离)
│   ├── spatial_analysis.py         # 🗺 空间分析 (网格OD矩阵/DBSCAN/净流量)
│   ├── visualization.py            # 📊 Matplotlib + Folium 静态可视化
│   ├── web_app.py                  # 🌐 Flask 核心 (21 个 API + 2 页面 + MySQL 数据层)
│   ├── templates/                  # 🎨 Jinja2 HTML 模板
│   │   ├── base.html               #   基础框架 (CDN + header + footer)
│   │   ├── index.html              #   分析看板 (9 张图表卡片 Grid)
│   │   └── realtime.html           #   实时大屏 (全屏三栏暗黑风格)
│   └── static/                     # 📁 前端静态资源
│       ├── css/
│       │   ├── dashboard.css       #   分析看板样式 (响应式 Grid)
│       │   └── realtime.css        #   实时大屏样式 (暗黑科幻 + 发光边框)
│       └── js/
│           ├── echarts/shine.js    #   ECharts 主题
│           ├── core/               #   核心模块
│           │   ├── api.js          #   fetch 封装 (降级处理)
│           │   └── chart-manager.js#   ECharts 实例管理器
│           ├── charts/             #   9 个图表渲染模块
│           │   ├── hourly.js       #   📈 24h 折线图
│           │   ├── duration.js     #   ⏱ 时长柱状图
│           │   ├── period.js       #   🕐 时段对比
│           │   ├── hotspots.js     #   📍 热点排行
│           │   ├── distance.js     #   📏 距离分布
│           │   ├── speed.js        #   ⚡ 速度分布
│           │   ├── efficiency.js   #   🚖 车辆效率
│           │   ├── net-flow.js     #   🔄 净流入/流出
│           │   └── od-lines.js     #   🗺 深圳OD流向图
│           ├── dashboard.js        #   看板主入口 (并行加载 + 渐进渲染)
│           └── realtime.js         #   实时大屏逻辑 (地图/热力图/趋势/排行)
│
├── tax_data/                       # 📊 数据目录
│   ├── 乘车出行数据源.csv           #   原始GPS (71MB, 1,601,307 条)
│   └── taxi_sz.csv                 #   清洗后OD (1MB, 8,517 条)
│
├── output/                         # 📤 输出
│   ├── figures/                    #   Matplotlib 静态图表
│   └── reports/                    #   自动生成的分析报告
│
├── log/                            # 📝 更新日志 (项目规范要求)
│   ├── 开发思想.md                  #   740行完整技术架构文档
│   ├── 数据清洗的数学思想.md         #   17个数学维度深度剖析
│   ├── init_20260626.md            #   🏗 项目初始化
│   ├── update_20260627.md          #   📋 Flask 平台 + 本地可视化
│   ├── update_20260627_web.md      #   🌐 Web 平台化重构
│   ├── update_20260627_geo_od_map.md # 🗺 深圳地图 OD 流向图
│   ├── fix_20260627_flask_sankey.md  # 🐛 OD 桑基图循环修复
│   ├── update_20260628_realtime_dashboard.md  # 🖥 实时运行态势大屏
│   └── update_20260628_lan_access.md # 🌐 局域网访问功能
│
├── notebooks/                      # 📓 Jupyter Notebook (EDA)
├── project_info/rule.md            # 📋 代码规范 + 图表参考
└── final_result/                   # 🎯 预期效果图 + 实现方案
```

---

## 🚀 快速开始

### 环境要求

| 环境 | Python | 说明 |
|:---|:---|:---|
| **推荐** | `3.8.10`（`.venv_py38`） | 所有依赖已安装 |
| 备用 | `3.12.4`（`.venv`） | 缺少 Flask，main.py 自动转发 |
| 数据库 | MySQL 8.0.13 | 虚拟机 192.168.116.128:3306 |

### 1. 安装

**Windows（一键）**：
```bash
setup_win.bat
# 自动: 下载 Python 3.8.10 → 创建 .venv_py38 → pip install
```

**手动**：
```bash
# Python 3.8
python3.8 -m venv .venv_py38
.venv_py38\Scripts\activate          # Windows
source .venv_py38/bin/activate       # Linux/Mac
pip install -r requirements_py38.txt
```

### 2. 运行

```bash
python main.py              # 完整分析 (清洗 → 分析 → 可视化)
python main.py --clean      # 仅数据清洗
python main.py --web        # 启动 Web 服务 (分析看板 + 实时大屏)
python main.py --report     # 仅生成报告
```

> 💡 **venv 自动检测**：`main.py` 自动检查当前 Python 是否有 Flask，若无则自动切换到 `.venv_py38`。

### 3. 访问

启动后浏览器打开:
- **分析看板**: http://localhost:5000/
- **实时大屏**: http://localhost:5000/realtime

### 4. 局域网共享 (可选)

让手机/平板/其他电脑也能访问:

```bash
# Windows — 右键以管理员身份运行
setup_firewall.bat

# Linux
sudo bash setup_firewall.sh
```

启动时控制台会自动显示局域网访问 URL（如 `http://192.168.x.x:5000`）。

---

## 📊 Web 看板

### 分析看板 (9 张图表)

| # | 图表 | 类型 | API | 说明 |
|:---:|:---|:---|:---|:---|
| 1 | 📈 24h 出行量分布 | Line | `/api/hourly` | 平滑折线 + 均值参考线 |
| 2 | ⏱ 行程时长分布 | Bar | `/api/duration` | 7 段分箱 + 统计面板 |
| 3 | 🕐 各时段出行量对比 | Bar | `/api/period` | 4 时段 (早高峰/平峰/晚高峰/夜间) |
| 4 | 📍 Top-15 出行热点 | H.Bar | `/api/hotspots` | DBSCAN 聚类 Top-15 |
| 5 | 📏 行程距离分布 | Bar | `/api/distance` | 7 段分箱 + 短途/长途占比 |
| 6 | ⚡ 行程速度分布 | Bar | `/api/speed` | 8 段分箱 + 均值标记线 |
| 7 | 🚖 车辆运营效率 | H.Bar | `/api/vehicles` | Top-15 车辆载客统计 |
| 8 | 🔄 区域净流入/流出 | Div.Bar | `/api/net-flow` | ±15 红绿发散配色 |
| 9 | 🗺 深圳 OD 流向图 | Geo+Graph | `/api/od-flows` | GeoJSON 地图 + 29 节点 + 25 条箭头 |

### 实时大屏 (暗黑科幻全屏)

```
┌──────────────────────────────────────────────────┐
│         🚕 深圳市出租车实时运行态势                  │  标题栏
├──────┬──────┬──────┬──────┬──────┤
│ 📊8,517│ 🚖353 │ ⏱11.9│ 📏2.46│ ⚡13.1│  KPI 卡片
├──────┼──────┴──────┼──────┤
│ 🏆热点 │ 🗺 Leaflet 地图  │ 📈 双Y轴趋势  │
│ 排行  │  + 热力图叠加   │    (出行量+速度) │
│ (列表) │  CartoDB 深色   │ 🕐 时段对比    │
├──────┴─────────────┴──────┤
│ MySQL @ 192.168.116.128 │ 🕐 时钟 │ 版权  │  底部
└──────────────────────────────────────────────────┘
```

---

## 🌐 API 端点 (21 个)

### 分析看板 API (11 个 — 内存数据源)

| 端点 | 方法 | 说明 |
|:---|:---|:---|
| `/` | GET | 分析看板主页 |
| `/realtime` | GET | 🖥 实时运行态势大屏 |
| `/api/kpis` | GET | 5 项 KPI (总出行量/车辆/时长/高峰) |
| `/api/hourly` | GET | 24h 出行量分布 |
| `/api/duration` | GET | 7 段时长分布 |
| `/api/period` | GET | 4 时段出行量对比 |
| `/api/hotspots` | GET | Top-15 出行热点 |
| `/api/distance` | GET | 7 段距离分布 + 统计指标 |
| `/api/speed` | GET | 8 段速度分布 + 统计指标 |
| `/api/vehicles` | GET | 车辆运营效率 Top-15 |
| `/api/od-flows` | GET | 深圳 OD 流向图 (nodes + edges) |
| `/api/net-flow` | GET | 净流入/流出 ±15 |

### 实时大屏 API (8 个 — MySQL 数据源)

| 端点 | 方法 | 说明 |
|:---|:---|:---|
| `/api/realtime/kpis` | GET | KPI 指标 (行程/车辆/时长/距离/速度) |
| `/api/realtime/heatmap` | GET | 500 个热力坐标点 |
| `/api/realtime/ranking` | GET | Top-15 热点排行 |
| `/api/realtime/trend` | GET | 24h 趋势 (出行量 + 速度双Y轴) |
| `/api/realtime/period` | GET | 4 时段出行量对比 |
| `/api/realtime/hourly` | GET | 24h 出行量分布 |
| `/api/realtime/dashboard` | GET | 聚合所有实时数据 |
| `/api/dashboard` | GET | 聚合所有数据 (向后兼容) |

### 基础设施

| 端点 | 方法 | 说明 |
|:---|:---|:---|
| `/api/health` | GET | 健康检查 |

---

## 🗄️ MySQL 数据库

| 表名 | 行数 | 说明 |
|------|------|------|
| `gps_trajectory` | 99,837 | GPS 轨迹采样 (前 10 万条) |
| `od_trips` | 8,517 | OD 行程数据 (完整) |
| `realtime_stats` | 45 | 预计算聚合缓存 (KPI/排行/趋势/热力图) |

**连接信息**: `192.168.116.128:3306` / `taxi_analysis`

---

## 🧹 数据清洗规则

```
160万GPS → [规则①异常坐标] → [规则②速度插值] → [规则③④行程切片+OD提取]
         → [规则⑤异常行程过滤] → 8,517 条有效OD行程 (188:1)
```

| 规则 | 操作 | 效果 | 核心数学 |
|------|------|------|----------|
| ① | 过滤超出深圳范围 (113.5°~114.5°, 22.4°~22.9°) 的坐标 | 1,601,307 → 1,599,329 | 集合论 + 超矩形交集 |
| ② | 异常速度 (<0 or >150) 线性插值填充 | 保持时间序列连续性 | 数值分析 (Lagrange 插值) |
| ③④ | 按 OpenStatus 状态机 (1→0→1) 切片提取 | → 16,783 段行程 | FSM + 双指针 O(n) 配对 |
| ⑤ | 过滤不合理时长/距离/速度 | → **8,517** 条 | Haversine + 统计 + 布尔代数 |

> 📖 更多: [数据清洗的数学思想](log/数据清洗的数学思想.md)

---

## 🔬 核心功能

| 模块 | 功能 | 技术 |
|:---|:---|:---|
| 数据预处理 | CSV 导入、编码检测、质量报告、5 条规则清洗 | Pandas / NumPy |
| 时序分析 | 24h 分布、高峰识别 (1.5× 阈值)、时长/距离统计、车辆效率 | 统计矩 / 极值理论 |
| 空间分析 | 101×56 网格 OD 矩阵、DBSCAN 聚类 (28)、净流量分析 | 矩阵代数 / 密度聚类 |
| 静态可视化 | Matplotlib 图表、Folium 热力地图 | Matplotlib / Seaborn |
| 分析看板 | 9 张 ECharts 图表、5 项 KPI、响应式 Grid | ECharts 5.5 + shine 主题 |
| 深圳 OD 流向 | GeoJSON 地图 + graph/geo 系列 | DataV GeoAtlas + ECharts |
| 实时大屏 | Leaflet 热力图 + 双 Y 轴趋势 + 排行联动 | Leaflet 1.9.4 + Leaflet.Heat |
| 数据库集成 | MySQL 8.0 + 预计算聚合缓存 | PyMySQL 1.1.1 |
| 局域网共享 | 防火墙一键配置 + IP 自动检测 | Python socket |

---

## 📦 核心依赖

| 组件 | 版本 | 用途 |
|:---|:---|:---|
| Python | 3.8.10 / 3.12.4 | 运行环境 |
| Pandas | 1.5.3 / 2.0+ | 数据处理 |
| NumPy | 1.23.5 / 1.24+ | 数值计算 |
| Matplotlib | 3.7.5 | 静态图表 |
| Seaborn | 0.13.2 | 统计可视化 |
| Folium | 0.14.0 | 交互式地图 |
| Scikit-learn | 1.3.2 | DBSCAN 聚类 |
| Flask | 2.2.5 | Web 服务 |
| Jinja2 | 3.1.4 | 模板引擎 |
| PyMySQL | 1.1.1 | MySQL 连接 |

### 前端 CDN

| 组件 | 版本 | 用途 |
|:---|:---|:---|
| ECharts | 5.5.0 | 图表引擎 |
| Leaflet | 1.9.4 | 地图底图 |
| Leaflet.Heat | 0.2.0 | 热力图叠加 |
| CartoDB Dark | — | 深色地图瓦片 |

---

## 📐 数据字段

### 原始 GPS (`乘车出行数据源.csv`)

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| VehicleNum | String | 车辆唯一标识 |
| Stime | Time | GPS 采集时刻 |
| Lng | Float | 经度 (WGS-84) |
| Lat | Float | 纬度 (WGS-84) |
| OpenStatus | Int | 0=载客, 1=空车 |
| Speed | Float | 瞬时速度 (km/h) |

### 清洗后 OD (`taxi_sz.csv`)

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| VehicleNum | String | 车辆唯一标识 |
| Stime | Time | 行程开始时刻 |
| SLng / SLat | Float | 起点经纬度 |
| ELng / ELat | Float | 终点经纬度 |
| Etime | Time | 行程结束时刻 |
| duration_min | Float | 行程时长 (分钟) |
| distance_km | Float | 行程距离 (公里, Haversine) |
| avg_speed | Float | 平均速度 (km/h) |

---

## 🌐 局域网访问

同一局域网内的其他设备（手机、平板、其他电脑）可直接访问。

### 为什么可以

Flask 绑定 `0.0.0.0` 监听所有网络接口，不只是 localhost。唯一可能的阻碍是 **操作系统防火墙**。

### 配置步骤

```bash
# Windows — 右键管理员运行
setup_firewall.bat

# Linux
sudo bash setup_firewall.sh
```

启动项目后，控制台会显示局域网 URL:
```
🌐 局域网访问 (同局域网设备):
├─ http://192.168.x.x:5000/        (分析看板)
└─ http://192.168.x.x:5000/realtime (实时大屏)
```

> 📖 更多: [局域网访问功能更新日志](log/update_20260628_lan_access.md)

---

## 🐧 CentOS 7 部署

```bash
# 1. 传输项目文件到虚拟机
# 2. 安装依赖
bash setup_vm.sh

# 3. 配置防火墙
sudo bash setup_firewall.sh

# 4. 启动
python main.py --web
```

---

## 📝 技术特性

| 特性 | 说明 |
|------|------|
| **venv 自动检测** | main.py 启动时自动查找可用虚拟环境 |
| **shine 主题** | 分析看板所有图表统一 ECharts shine 暗色主题 |
| **dark 主题** | 实时大屏 ECharts dark + 自定义暗黑 CSS |
| **渐进加载** | 10 个 API 并行 fetch，数据到达即渲染 |
| **降级处理** | 任一 API 失败不影响其他图表 |
| **响应式** | CSS Grid `auto-fit minmax(500px, 1fr)` + resize 监听 |
| **深圳地图** | DataV GeoAtlas GeoJSON + `echarts.registerMap` + graph |
| **深色地图** | CartoDB Dark Matter 瓦片 (免 API Key) |
| **排行联动** | 点击排行项 → 地图 flyTo 定位 |
| **30 秒刷新** | 实时大屏自动轮询 MySQL 最新数据 |
| **LAN 共享** | 防火墙一键配置 + IP 自动检测 |

---

## 📋 更新日志

| 日期 | 说明 | 详情 |
|:---|:---|:---|
| **2026-06-28** | 🌐 **局域网访问** | 防火墙配置 + IP 自动检测 + 启动 URL 提示 | [log](log/update_20260628_lan_access.md) |
| **2026-06-28** | 🖥 **实时运行态势大屏** | MySQL 数据源 + 暗黑科幻 + Leaflet 热力图 + 双Y轴趋势 | [log](log/update_20260628_realtime_dashboard.md) |
| 2026-06-27 | 🗺 深圳地图 OD 流向图 | 桑基图 → Geo+Graph 深圳行政区地图 | [log](log/update_20260627_geo_od_map.md) |
| 2026-06-27 | 🔧 Flask 启动修复 | main.py 添加 venv 自动检测转发 | [log](log/fix_20260627_flask_sankey.md) |
| 2026-06-27 | 🌐 Web 平台化重构 | Jinja2 模板 + 静态文件分离 + 10 个 API | [log](log/update_20260627_web.md) |
| 2026-06-27 | 📊 新增 5 张图表 | 距离/速度/效率/净流量/OD 流向 | [log](log/update_20260627_web.md) |
| 2026-06-27 | 🐛 OD 桑基图循环修复 | Kahn 拓扑排序消除 DAG 循环 | [log](log/fix_20260627_flask_sankey.md) |
| 2026-06-27 | 📋 初始实现 | Flask 平台 + 本地可视化 | [log](log/update_20260627.md) |
| 2026-06-26 | 🏗 项目初始化 | 项目框架搭建 | [log](log/init_20260626.md) |

---

## 📖 深度文档

| 文档 | 内容 | 路径 |
|------|------|------|
| **开发思想** | 740 行完整技术架构、21 个 API 详解、前端数据流图、部署拓扑 | [log/开发思想.md](log/开发思想.md) |
| **数据清洗数学** | 17 个数学维度: Haversine/DBSCAN/FSM/插值/统计矩/矩阵代数 | [log/数据清洗的数学思想.md](log/数据清洗的数学思想.md) |

---

## License

内部项目 — 仅供项目组使用
