# -*- coding: utf-8 -*-
"""
PySpark 会话管理器
集中管理 SparkSession 的创建与销毁，支持:
  - remote: 连接 CentOS VM 上的 Spark 集群 (192.168.116.128:7077)
  - local:  本机多核并行 (local[*])
  - auto:   自动检测 (remote优先 → local → Pandas回退)

用法:
    from src.spark_manager import get_spark, spark_to_pandas

    spark = get_spark()
    if spark:
        sdf = spark.createDataFrame(pandas_df)
        result_df = spark_to_pandas(sdf)
    else:
        # 回退到 Pandas 处理
        result_df = pandas_processing()
"""

import os
import sys
import time

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import SPARK_CONFIG, SPARK_MODE, SPARK_MASTER_REMOTE, SPARK_MASTER_LOCAL
from .logger import get_logger

_spark_session = None
_spark_available = None  # None=未检测, True=可用, False=不可用
_spark_mode_used = None  # 实际使用的模式


def _check_pyspark():
    """检测 PySpark 是否可用"""
    try:
        import pyspark
        return True
    except ImportError:
        return False


def _try_connect_remote():
    """
    尝试连接远程 Spark 集群 (CentOS VM)

    Returns
    -------
    SparkSession or None
    """
    import socket
    host = "192.168.116.128"
    port = 7077
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_spark(app_name=None, master=None):
    """
    获取或创建全局 SparkSession

    优先级: 指定参数 > remote检测 > local > None(回退Pandas)

    Parameters
    ----------
    app_name : str, optional
        Spark 应用名称
    master : str, optional
        Spark master URL, 如 "spark://192.168.116.128:7077" 或 "local[*]"

    Returns
    -------
    SparkSession or None
        如果 PySpark 不可用返回 None
    """
    global _spark_session, _spark_available, _spark_mode_used

    # 如果已有会话，直接返回
    if _spark_session is not None:
        return _spark_session

    # 如果之前检测过不可用，返回 None
    if _spark_available is False:
        return None

    log = get_logger()

    # 检测 PySpark 是否安装
    if not _check_pyspark():
        log.warning("PySpark 未安装，将使用 Pandas 处理数据")
        _spark_available = False
        return None

    from pyspark.sql import SparkSession

    # 确定 master
    if master is None:
        mode = SPARK_MODE
        if mode == "remote":
            master = SPARK_MASTER_REMOTE
        elif mode == "local":
            master = SPARK_MASTER_LOCAL
        else:  # auto
            log.info("自动检测 Spark 集群...")
            if _try_connect_remote():
                master = SPARK_MASTER_REMOTE
                log.info(f"[OK] 检测到远程 Spark 集群: {master}")
            else:
                master = SPARK_MASTER_LOCAL
                log.info(f"远程 Spark 未响应，使用本机模式: {master}")

    app_name = app_name or SPARK_CONFIG.get("app_name", "TaxiTripAnalysis")

    try:
        builder = SparkSession.builder.appName(app_name).master(master)

        # 应用配置
        for key, value in SPARK_CONFIG.items():
            if key not in ("app_name", "master") and key.startswith("spark."):
                builder = builder.config(key, str(value))

        _spark_session = builder.getOrCreate()
        _spark_available = True
        _spark_mode_used = master

        log.info(f"PySpark 会话已创建 (master={master})")
        log.info(f"  Spark version: {_spark_session.version}")

        # 设置日志级别
        _spark_session.sparkContext.setLogLevel(
            SPARK_CONFIG.get("spark.log.level", "WARN")
        )

        return _spark_session

    except Exception as e:
        log.warning(f"PySpark 初始化失败: {e}")
        log.warning("将回退到 Pandas 处理数据")
        _spark_available = False
        _spark_session = None
        return None


def get_spark_mode():
    """获取当前使用的 Spark 模式"""
    return _spark_mode_used


def is_spark_available():
    """检查 PySpark 是否可用"""
    global _spark_available
    if _spark_available is None:
        get_spark()
    return _spark_available is True


def spark_to_pandas(sdf, n=None):
    """
    将 Spark DataFrame 转换为 Pandas DataFrame

    Parameters
    ----------
    sdf : pyspark.sql.DataFrame
        Spark DataFrame
    n : int, optional
        收集行数限制 (默认全部)

    Returns
    -------
    pd.DataFrame
    """
    import pandas as pd

    log = get_logger()
    start = time.time()

    if n is not None:
        sdf = sdf.limit(n)

    try:
        # 优先使用 Arrow 加速 (已在 SPARK_CONFIG 中启用)
        pdf = sdf.toPandas()
    except Exception:
        # Arrow 不可用时回退
        pdf = sdf.toPandas()

    elapsed = time.time() - start
    log.debug(f"Spark→Pandas 转换完成: {len(pdf):,} 行, 耗时 {elapsed:.2f}s")
    return pdf


def stop_spark():
    """停止 SparkSession"""
    global _spark_session, _spark_available, _spark_mode_used
    if _spark_session is not None:
        _spark_session.stop()
        _spark_session = None
        _spark_available = None
        _spark_mode_used = None
        get_logger().info("SparkSession 已停止")


def load_csv_to_spark(filepath, spark=None):
    """
    加载 CSV 文件到 Spark DataFrame

    Parameters
    ----------
    filepath : str
        CSV 文件路径
    spark : SparkSession, optional

    Returns
    -------
    tuple (Spark DataFrame, SparkSession) or (None, None)
    """
    spark = spark or get_spark()
    if spark is None:
        return None, None

    log = get_logger()
    log.info(f"PySpark 加载 CSV: {filepath}")
    start = time.time()

    # 自动检测编码后读取
    sdf = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .option("encoding", "UTF-8") \
        .csv(filepath)

    # 如果 UTF-8 失败，尝试 GBK (静默回退)
    try:
        _ = sdf.count()
    except Exception:
        sdf = spark.read \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .option("encoding", "GBK") \
            .csv(filepath)

    # 清理列名空格
    for col in sdf.columns:
        sdf = sdf.withColumnRenamed(col, col.strip())

    elapsed = time.time() - start
    row_count = sdf.count()
    log.info(f"CSV加载完成: {row_count:,} 行, {len(sdf.columns)} 列, 耗时 {elapsed:.2f}s")

    return sdf, spark
