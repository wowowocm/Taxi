# 城市出行数据分析系统 (Urban Travel Analysis System)

基于GPS轨迹数据的深圳市出租车出行行为分析系统

## 项目概述

本项目基于深圳市500辆出租车全天候GPS轨迹数据（约160万条记录），通过数据清洗、特征工程与可视化分析，挖掘城市居民出行模式。

## 项目结构

```
Taxi/
├── main.py                    # 项目主入口
├── requirements.txt           # Python依赖清单
├── README.md                  # 项目说明
├── src/                       # 源代码
│   ├── __init__.py
│   ├── config.py              # 全局配置
│   ├── data_loader.py         # 数据加载模块
│   ├── data_cleaner.py        # 数据清洗模块
│   ├── trip_extractor.py      # 行程提取模块
│   ├── temporal_analysis.py   # 时序分析模块
│   ├── spatial_analysis.py    # 空间分析模块
│   ├── visualization.py       # 可视化模块
│   └── web_app.py             # Flask Web应用
├── tax_data/                  # 数据目录
│   ├── 乘车出行数据源.csv      # 原始GPS数据
│   └── taxi_sz.csv            # 清洗后OD数据
├── notebooks/                 # Jupyter Notebook
├── output/                    # 输出目录
│   ├── figures/               # 图表输出
│   └── reports/               # 分析报告
├── project_info/              # 项目文档
├── final_result/              # 预期效果图
└── log/                       # 更新日志
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行分析

```bash
# 执行完整分析（数据加载 → 清洗 → 分析 → 可视化）
python main.py

# 仅数据清洗
python main.py --clean

# 启动Web交互看板
python main.py --web

# 仅生成分析报告
python main.py --report
```

### 3. 访问Web看板

启动Web服务后，浏览器访问: http://localhost:5000

## 功能模块

| 模块 | 功能 | 状态 |
|:---|:---|:---:|
| 数据预处理 | 数据导入、质量报告、自动清洗、行程提取 | ✅ |
| 时序分析 | 高峰识别、小时分布、时长/距离统计 | ✅ |
| 空间分析 | 热力分布、OD矩阵、DBSCAN聚类、净流量分析 | ✅ |
| 可视化展示 | Folium地图、Matplotlib图表、ECharts看板 | ✅ |

## 核心依赖

| 组件 | 版本 |
|:---|:---|
| Python | 3.8+ |
| Pandas | 2.0+ |
| NumPy | 1.24+ |
| Matplotlib | 3.7+ |
| Folium | 0.13+ |
| Scikit-learn | 1.3+ |
| Flask | 2.2+ |

## 部署到CentOS VM

1. 将项目文件传输至虚拟机
2. 安装依赖: `pip install -r requirements.txt`
3. 确保数据文件路径正确
4. 启动Web服务: `python main.py --web`

## 数据字段说明

### 原始GPS数据 (乘车出行数据源.csv)

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| VehicleNum | String | 车辆唯一标识 |
| Stime | Time | GPS采集时刻 |
| Lng | Float | GPS经度 (WGS-84) |
| Lat | Float | GPS纬度 (WGS-84) |
| OpenStatus | Int | 0=载客, 1=空车 |
| Speed | Float | 瞬时速度 (km/h) |

### 清洗后OD数据 (taxi_sz.csv)

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| VehicleNum | String | 车辆唯一标识 |
| Stime | Time | 行程开始时刻 |
| SLng/SLat | Float | 起点经纬度 |
| ELng/ELat | Float | 终点经纬度 |
| Etime | Time | 行程结束时刻 |

## 数据清洗规则

1. **异常坐标过滤** - 过滤超出深圳地理范围的GPS坐标
2. **异常速度处理** - 处理不合理的速度值
3. **载客行程切片** - 根据OpenStatus识别载客段落
4. **OD提取** - 提取每个行程的起止信息
5. **异常行程过滤** - 过滤时长/距离/速度不合理的行程

## License

内部项目 - 仅供项目组使用
