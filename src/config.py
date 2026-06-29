# -*- coding: utf-8 -*-
"""
项目全局配置文件
统一管理所有可配置参数，便于调整和维护
"""

import os

# ============================================================
# 项目路径配置
# ============================================================
# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据目录
DATA_DIR = os.path.join(ROOT_DIR, "tax_data")
RAW_DATA_PATH = os.path.join(DATA_DIR, "乘车出行数据源.csv")
CLEANED_DATA_PATH = os.path.join(DATA_DIR, "taxi_sz.csv")

# 输出目录
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
FIGURES_DIR = os.path.join(OUTPUT_DIR, "figures")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")

# 日志目录
LOG_DIR = os.path.join(ROOT_DIR, "log")

# Notebook目录
NOTEBOOKS_DIR = os.path.join(ROOT_DIR, "notebooks")

# ============================================================
# 深圳地理范围配置
# ============================================================
SHENZHEN_LNG_MIN = 113.5   # 最小经度
SHENZHEN_LNG_MAX = 114.5   # 最大经度
SHENZHEN_LAT_MIN = 22.4    # 最小纬度
SHENZHEN_LAT_MAX = 22.9    # 最大纬度

# ============================================================
# 数据清洗参数
# ============================================================
# 异常速度阈值
SPEED_MIN = 0        # 最小合理速度 (km/h)
SPEED_MAX = 150      # 最大合理速度 (km/h)

# 异常行程过滤阈值
TRIP_DURATION_MIN = 1       # 最小行程时长 (分钟)
TRIP_DURATION_MAX = 240     # 最大行程时长 (分钟, 4小时)
TRIP_DISTANCE_MIN = 0.2     # 最小行程距离 (公里, 200米)
TRIP_AVG_SPEED_MIN = 5      # 最小平均速度 (km/h)
TRIP_AVG_SPEED_MAX = 100    # 最大平均速度 (km/h)

# ============================================================
# 时段划分配置
# ============================================================
TIME_PERIODS = {
    "早高峰": ("07:00", "09:00"),
    "日间平峰": ("09:00", "17:00"),
    "晚高峰": ("17:00", "19:00"),
    "夜间": ("19:00", "23:59"),
}

# 按小时时段
HOUR_LABELS = [f"{h:02d}:00" for h in range(24)]

# ============================================================
# 空间分析参数
# ============================================================
# 网格大小 (OD矩阵, 单位: 度, 约1km)
GRID_SIZE_LNG = 0.01   # 经度间隔 (~1km)
GRID_SIZE_LAT = 0.009  # 纬度间隔 (~1km)

# DBSCAN聚类参数
DBSCAN_EPS = 0.005     # 聚类半径 (约500m)
DBSCAN_MIN_SAMPLES = 20  # 最小样本数

# 热点区域Top-N
TOP_N_HOTSPOTS = 20

# ============================================================
# 可视化参数
# ============================================================
# 地图默认中心 (深圳中心)
MAP_CENTER = [22.65, 114.05]
MAP_DEFAULT_ZOOM = 11

# 图表默认样式
CHART_STYLE = {
    "figure.dpi": 150,
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,  # 正确显示负号
}

# ============================================================
# 性能参数
# ============================================================
# Pandas显示选项
PANDAS_MAX_ROWS = 100
PANDAS_MAX_COLUMNS = 20

# 分批处理大小 (用于大文件)
CHUNK_SIZE = 100000

# ============================================================
# 报告参数
# ============================================================
REPORT_TITLE = "深圳市出租车出行行为分析报告"
REPORT_AUTHOR = "数据分析项目组"

# ============================================================
# Flask Web服务配置
# ============================================================
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True

# ============================================================
# MySQL配置 (CentOS VM)
# ============================================================
MYSQL_CONFIG = {
    "host": "192.168.116.128",
    "port": 3306,
    "user": "root",
    "password": "mysql123456",
    "database": "taxi_analysis",
    "charset": "utf8mb4",
}

# ============================================================
# PySpark配置 (用于大规模数据处理)
# ============================================================

# Spark运行模式: "remote" (VM集群), "local" (本机), "auto" (自动检测)
SPARK_MODE = "auto"

# VM Spark 集群地址
SPARK_MASTER_REMOTE = "spark://192.168.116.128:7077"
SPARK_MASTER_LOCAL = "local[*]"

SPARK_CONFIG = {
    "app_name": "TaxiTripAnalysis",
    "master": SPARK_MASTER_LOCAL,  # 默认值，运行时根据 SPARK_MODE 动态切换
    # Spark executor/driver 配置
    "spark.executor.memory": "2g",
    "spark.driver.memory": "1g",
    "spark.sql.shuffle.partitions": "8",
    "spark.executor.cores": "2",
    # PySpark ↔ Pandas 互转优化
    "spark.sql.execution.arrow.pyspark.enabled": "true",
    # 日志级别
    "spark.log.level": "WARN",
}

# ============================================================
# 数据上传到MySQL的配置
# ============================================================
UPLOAD_TO_MYSQL = True  # 是否将分析结果上传到MySQL
MYSQL_UPLOAD_TABLES = {
    "od_trips": "清洗后的OD行程数据",
    "hourly_stats": "24小时出行量统计",
    "period_stats": "时段统计",
    "hotspots": "出行热点区域",
    "vehicle_efficiency": "车辆运营效率",
    "net_flow": "净流入流出分析",
}
