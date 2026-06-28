# 城市出行数据分析系统 (Urban Travel Analysis System)

基于GPS轨迹数据的深圳市出租车出行行为分析系统

## 项目概述

本项目基于深圳市500辆出租车全天候GPS轨迹数据（约160万条记录），通过数据清洗、特征工程与可视化分析，挖掘城市居民出行模式。

## 项目结构

```
Taxi/
├── main.py                         # 项目主入口（支持 venv 自动检测）
├── requirements.txt                # Python 3.12 依赖清单
├── requirements_py38.txt           # Python 3.8 依赖清单（推荐）
├── setup_win.bat                   # Windows 一键安装脚本
├── setup_vm.sh                     # CentOS 部署脚本
├── README.md                       # 项目说明
├── src/                            # 源代码
│   ├── __init__.py
│   ├── config.py                   # 全局配置
│   ├── logger.py                   # 日志模块
│   ├── data_loader.py              # 数据加载模块
│   ├── data_cleaner.py             # 数据清洗模块
│   ├── trip_extractor.py           # 行程提取模块
│   ├── temporal_analysis.py        # 时序分析模块
│   ├── spatial_analysis.py         # 空间分析模块（OD矩阵、DBSCAN、净流量）
│   ├── visualization.py            # Matplotlib 可视化模块
│   ├── web_app.py                  # Flask Web 应用（13个API端点）
│   ├── templates/                  # Jinja2 模板
│   │   ├── base.html               # 基础模板（CDN + shine 主题）
│   │   └── index.html              # 看板页面（9张图表卡片）
│   └── static/                     # 静态资源
│       ├── css/dashboard.css       # 看板样式（响应式 Grid）
│       └── js/
│           ├── echarts/shine.js    # ECharts shine 主题
│           ├── core/
│           │   ├── api.js          # fetch 封装（降级处理）
│           │   └── chart-manager.js # ECharts 实例管理器
│           ├── charts/             # 图表模块（9个）
│           │   ├── hourly.js       # 24h 出行量折线图
│           │   ├── duration.js     # 时长柱状图
│           │   ├── period.js       # 时段对比图
│           │   ├── hotspots.js     # 热点水平柱状图
│           │   ├── distance.js     # 距离分布
│           │   ├── speed.js        # 速度分布
│           │   ├── efficiency.js   # 车辆效率
│           │   ├── net-flow.js     # 净流入/流出
│           │   └── od-lines.js     # 🗺 深圳地图OD流向图
│           └── dashboard.js        # 主入口（渐进加载）
├── tax_data/                       # 数据目录
│   ├── 乘车出行数据源.csv           # 原始GPS数据
│   └── taxi_sz.csv                 # 清洗后OD数据（8,517条行程）
├── notebooks/                      # Jupyter Notebook
├── output/                         # 输出目录
│   ├── figures/                    # Matplotlib 图表
│   └── reports/                    # 分析报告
├── project_info/                   # 项目文档
│   └── rule.md                     # 代码规范 + 图表参考
├── final_result/                   # 预期效果图
└── log/                            # 更新日志
```

## 快速开始

### 环境要求

| 环境 | Python | 说明 |
|:---|:---|:---|
| **推荐** | `3.8.10`（`.venv_py38`） | 所有依赖已安装，直接使用 |
| 备用 | `3.12.4`（`.venv`） | 缺少 Flask，main.py 会自动转发 |

### 1. 环境安装

**Windows（推荐）**：
```bash
setup_win.bat
# 自动下载 Python 3.8.10、创建 .venv_py38、安装依赖
```

**手动**：
```bash
# Python 3.8
python3.8 -m venv .venv_py38
.venv_py38\Scripts\activate     # Windows
source .venv_py38/bin/activate  # Linux/Mac
pip install -r requirements_py38.txt
```

### 2. 运行分析

```bash
# 执行完整分析（数据加载 → 清洗 → 分析 → 可视化）
python main.py

# 仅数据清洗
python main.py --clean

# 启动 Web 交互看板（自动检测 venv）
python main.py --web

# 仅生成分析报告
python main.py --report
```

> **💡 venv 自动检测**：`main.py` 启动时自动检查当前 Python 是否有 Flask，若无则自动切换到 `.venv_py38`。无需手动激活虚拟环境。

### 3. 访问 Web 看板

启动后浏览器访问 **http://localhost:5000**

## Web 看板图表

| # | 图表 | 类型 | API 端点 | 说明 |
|:---:|:---|:---|:---|:---|
| 1 | 📈 24小时出行量分布 | Line | `/api/hourly` | 平滑折线 + 均值参考线 |
| 2 | ⏱ 行程时长分布 | Bar | `/api/duration` | 7段分箱 + 统计面板 |
| 3 | 🕐 各时段出行量对比 | Bar | `/api/period` | 4时段（早高峰/平峰/晚高峰/夜间） |
| 4 | 📍 Top-15 出行热点 | H.Bar | `/api/hotspots` | DBSCAN 聚类 Top-15 |
| 5 | 📏 行程距离分布 | Bar | `/api/distance` | 7段分箱 + 短途/长途占比 |
| 6 | ⚡ 行程速度分布 | Bar | `/api/speed` | 8段分箱 + 均值标记线 |
| 7 | 🚖 车辆运营效率 | H.Bar | `/api/vehicles` | Top-15 车辆载客统计 |
| 8 | 🔄 区域净流入/流出 | Div.Bar | `/api/net-flow` | ±15 红绿发散配色 |
| 9 | 🗺 深圳地图OD流向图 | Geo+Graph | `/api/od-flows` | 深圳行政区地图 + 29节点 + 25条箭头连线 |

### 技术特性

- **shine 主题** — 所有图表统一 ECharts shine 暗色主题
- **渐进加载** — 10 个 API 并行 fetch，数据到达即渲染
- **降级处理** — 任一 API 失败不影响其他图表
- **响应式** — CSS Grid `auto-fit minmax(500px, 1fr)` + resize 监听
- **深圳地图** — DataV GeoAtlas GeoJSON + `echarts.registerMap` + graph 系列
- **venv 自动检测** — `main.py` 运行前自动查找可用虚拟环境

## API 端点（13个）

| 端点 | 说明 |
|:---|:---|
| `/realtime` | 🖥 实时大屏 | 暗黑科幻风全屏实时运行态势 |
| `/` | Jinja2 模板渲染主页 | 原始分析看板 |
| `/api/kpis` | 5项 KPI 卡片 |
| `/api/hourly` | 24h 出行量 |
| `/api/duration` | 时长分布（7段） |
| `/api/period` | 4时段占比 |
| `/api/hotspots` | Top-15 热点 |
| `/api/distance` | 距离分布（7段） |
| `/api/speed` | 速度分布（8段） |
| `/api/vehicles` | 车辆效率 Top-15 |
| `/api/od-flows` | 深圳OD流向数据 |
| `/api/net-flow` | 净流入/流出 ±15 |
| `/api/dashboard` | 聚合端点（向后兼容） |
| `/api/health` | 健康检查 |

## 核心功能

| 模块 | 功能 | 状态 |
|:---|:---|:---:|
| 数据预处理 | 数据导入、质量报告、自动清洗、行程提取 | ✅ |
| 时序分析 | 高峰识别、小时分布、时长/距离统计、车辆效率 | ✅ |
| 空间分析 | OD矩阵、DBSCAN聚类、热力分布、净流量分析 | ✅ |
| 可视化 | Matplotlib 图表、Folium 热力地图、ECharts 交互看板 | ✅ |
| Web 看板 | Jinja2 模板、13个API、响应式布局、venv 自动检测 | ✅ |
| 深圳地图 | GeoJSON 地图注册、graph 系列 OD 流向图 | ✅ |

## 核心依赖

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

## 数据字段说明

### 原始GPS数据 (`乘车出行数据源.csv`)

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| VehicleNum | String | 车辆唯一标识 |
| Stime | Time | GPS采集时刻 |
| Lng | Float | GPS经度 (WGS-84) |
| Lat | Float | GPS纬度 (WGS-84) |
| OpenStatus | Int | 0=载客, 1=空车 |
| Speed | Float | 瞬时速度 (km/h) |

### 清洗后OD数据 (`taxi_sz.csv`)

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| VehicleNum | String | 车辆唯一标识 |
| Stime | Time | 行程开始时刻 |
| SLng / SLat | Float | 起点经纬度 |
| ELng / ELat | Float | 终点经纬度 |
| Etime | Time | 行程结束时刻 |
| duration_min | Float | 行程时长（分钟） |
| distance_km | Float | 行程距离（公里） |
| avg_speed | Float | 平均速度（km/h） |

## 数据清洗规则

1. **异常坐标过滤** — 过滤超出深圳地理范围的GPS坐标（1,601,307 → 1,599,329）
2. **行程切片与OD提取** — 根据 OpenStatus 识别载客段落，提取起止点（→ 16,783 段）
3. **异常行程过滤** — 过滤时长/距离/速度不合理的行程（→ 8,517 条有效行程）

## 部署到 CentOS 7 VM

1. 将项目文件传输至虚拟机
2. 安装依赖：`bash setup_vm.sh`
3. 确保数据文件路径正确
4. 启动 Web 服务：`python main.py --web`

## 更新日志

| 日期 | 说明 | 详情 |
|:---|:---|:---|
| 2026-06-28 | 🖥 实时运行态势大屏 | MySQL数据源 + 暗黑科幻大屏 + Leaflet热力图 + 双Y轴趋势 | [log](log/update_20260628_realtime_dashboard.md) |
| 2026-06-27 | 🗺 深圳地图 OD 流向图 | 桑基图 → Geo+Graph 深圳行政区地图流向图 | [log](log/update_20260627_geo_od_map.md) |
| 2026-06-27 | 🔧 Flask 启动修复 | main.py 添加 venv 自动检测转发 | [log](log/fix_20260627_flask_sankey.md) |
| 2026-06-27 | 🌐 Web 平台化重构 | Jinja2 模板 + 静态文件分离 + 10个API | [log](log/update_20260627_web.md) |
| 2026-06-27 | 📊 新增5张图表 | 距离/速度/效率/净流量/OD流向 | [log](log/update_20260627_web.md) |
| 2026-06-27 | 🐛 OD桑基图循环修复 | Kahn拓扑排序消除DAG循环 | [log](log/fix_20260627_flask_sankey.md) |
| 2026-06-27 | 📋 初始实现 | flask平台实现 + 本地可视化 | [log](log/update_20260627.md) |
| 2026-06-26 | 🏗 项目初始化 | 项目框架搭建 | [log](log/init_20260626.md) |

## License

内部项目 — 仅供项目组使用
