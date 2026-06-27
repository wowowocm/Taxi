# -*- coding: utf-8 -*-
"""
数据加载模块
负责CSV数据导入、字段识别、编码检测、数据质量报告生成
"""

import os
import time
import pandas as pd
import numpy as np
from .config import (
    RAW_DATA_PATH, CLEANED_DATA_PATH, SHENZHEN_LNG_MIN,
    SHENZHEN_LNG_MAX, SHENZHEN_LAT_MIN, SHENZHEN_LAT_MAX,
    PANDAS_MAX_ROWS, PANDAS_MAX_COLUMNS, CHUNK_SIZE,
)
from .logger import get_logger

# 设置Pandas显示选项
pd.set_option("display.max_rows", PANDAS_MAX_ROWS)
pd.set_option("display.max_columns", PANDAS_MAX_COLUMNS)


class DataLoader:
    """数据加载器，支持原始GPS数据和清洗后OD数据的导入"""

    def __init__(self):
        self.raw_df = None       # 原始GPS数据
        self.cleaned_df = None   # 清洗后OD数据
        self.raw_stats = {}      # 原始数据统计
        self.cleaned_stats = {}  # 清洗数据统计

    # ----------------------------------------------------------
    # 数据导入
    # ----------------------------------------------------------
    def load_raw_data(self, filepath: str = None) -> pd.DataFrame:
        """
        导入原始GPS轨迹数据

        Parameters
        ----------
        filepath : str, optional
            数据文件路径，默认使用配置中的路径

        Returns
        -------
        pd.DataFrame
            包含 VehicleNum, Stime, Lng, Lat, OpenStatus, Speed 的DataFrame
        """
        path = filepath or RAW_DATA_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"数据文件不存在: {path}")

        log = get_logger()
        log.info(f"正在加载原始GPS数据: {path}")
        start = time.time()

        # 自动检测编码
        encoding = self._detect_encoding(path)
        log.info(f"检测到文件编码: {encoding}")

        # 读取CSV
        self.raw_df = pd.read_csv(path, encoding=encoding)

        # 统一列名（去除可能存在的空格）
        self.raw_df.columns = self.raw_df.columns.str.strip()

        elapsed = time.time() - start
        log.info(f"数据加载完成! 耗时: {elapsed:.2f}秒")
        log.info(f"记录数: {len(self.raw_df):,}, 字段数: {len(self.raw_df.columns)}")

        return self.raw_df

    def load_cleaned_data(self, filepath: str = None) -> pd.DataFrame:
        """
        导入清洗后的出行OD数据

        Parameters
        ----------
        filepath : str, optional
            数据文件路径

        Returns
        -------
        pd.DataFrame
            包含 VehicleNum, Stime, SLng, SLat, ELng, ELat, Etime 的DataFrame
        """
        path = filepath or CLEANED_DATA_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"数据文件不存在: {path}")

        print(f"[INFO] 正在加载清洗后OD数据: {path}")
        start = time.time()

        self.cleaned_df = pd.read_csv(path)
        self.cleaned_df.columns = self.cleaned_df.columns.str.strip()

        elapsed = time.time() - start
        print(f"[INFO] 数据加载完成! 耗时: {elapsed:.2f}秒")
        print(f"[INFO] 记录数: {len(self.cleaned_df):,}")

        return self.cleaned_df

    # ----------------------------------------------------------
    # 数据质量报告
    # ----------------------------------------------------------
    def generate_quality_report(self, df: pd.DataFrame = None) -> dict:
        """
        生成数据质量评估报告

        Parameters
        ----------
        df : pd.DataFrame, optional
            待评估的DataFrame，默认使用已加载的原始数据

        Returns
        -------
        dict
            包含各项质量指标的字典
        """
        if df is None:
            if self.raw_df is None:
                self.load_raw_data()
            df = self.raw_df

        print("\n" + "=" * 60)
        print("  数据质量评估报告")
        print("=" * 60)

        # 基础统计
        total = len(df)
        vehicles = df["VehicleNum"].nunique() if "VehicleNum" in df.columns else 0

        print(f"\n--- 基础统计 ---")
        print(f"  总记录数: {total:,}")
        print(f"  车辆数量: {vehicles}")

        # 时间跨度
        if "Stime" in df.columns:
            print(f"  时间跨度: {df['Stime'].min()} ~ {df['Stime'].max()}")

        # 缺失值统计
        print(f"\n--- 缺失值统计 ---")
        missing = df.isnull().sum()
        for col, count in missing.items():
            pct = count / total * 100 if total > 0 else 0
            print(f"  {col}: {count:,} ({pct:.2f}%)")

        # 异常坐标检测
        if "Lng" in df.columns and "Lat" in df.columns:
            abnormal = (
                (df["Lng"] < SHENZHEN_LNG_MIN) |
                (df["Lng"] > SHENZHEN_LNG_MAX) |
                (df["Lat"] < SHENZHEN_LAT_MIN) |
                (df["Lat"] > SHENZHEN_LAT_MAX)
            )
            abnormal_count = abnormal.sum()
            print(f"\n--- 坐标质量 ---")
            print(f"  异常坐标记录: {abnormal_count:,} ({abnormal_count/total*100:.2f}%)")
            print(f"  有效坐标记录: {total - abnormal_count:,} ({(total-abnormal_count)/total*100:.2f}%)")

        # 载客状态分布
        if "OpenStatus" in df.columns:
            occupied = (df["OpenStatus"] == 0).sum()
            empty = (df["OpenStatus"] == 1).sum()
            print(f"\n--- 载客状态分布 ---")
            print(f"  载客(OpenStatus=0): {occupied:,} ({occupied/total*100:.1f}%)")
            print(f"  空车(OpenStatus=1): {empty:,} ({empty/total*100:.1f}%)")

        # 速度分布
        if "Speed" in df.columns:
            speed = df["Speed"]
            print(f"\n--- 速度分布 (km/h) ---")
            print(f"  均值: {speed.mean():.2f}")
            print(f"  中位数: {speed.median():.2f}")
            print(f"  标准差: {speed.std():.2f}")
            print(f"  最大值: {speed.max():.2f}")

            # 速度分段统计
            speed_bins = [0, 1, 20, 40, 60, float("inf")]
            speed_labels = ["静止(0)", "低速(1-20)", "中速(20-40)", "快速(40-60)", "超快(>60)"]
            speed_segments = pd.cut(speed, bins=speed_bins, labels=speed_labels, right=True)
            print(f"\n  速度分段:")
            for label, count in speed_segments.value_counts().items():
                print(f"    {label}: {count:,} ({count/total*100:.1f}%)")

        print("\n" + "=" * 60)

        # 保存统计结果
        self.raw_stats = {
            "total_records": total,
            "vehicle_count": vehicles,
            "missing_values": missing.to_dict(),
            "abnormal_coords": abnormal_count if "Lng" in df.columns else 0,
        }

        return self.raw_stats

    def generate_od_report(self, df: pd.DataFrame = None) -> dict:
        """
        生成OD数据统计报告

        Parameters
        ----------
        df : pd.DataFrame, optional
            OD数据DataFrame

        Returns
        -------
        dict
            OD数据统计信息
        """
        if df is None:
            if self.cleaned_df is None:
                self.load_cleaned_data()
            df = self.cleaned_df

        print("\n" + "=" * 60)
        print("  OD出行数据统计报告")
        print("=" * 60)

        total_trips = len(df)
        total_vehicles = df["VehicleNum"].nunique()

        print(f"\n--- 基础统计 ---")
        print(f"  总行程数: {total_trips:,}")
        print(f"  车辆数: {total_vehicles:,}")
        print(f"  单车日均行程: {total_trips/total_vehicles:.1f} 次")

        # 时间段分布（如果有Stime字段）
        if "Stime" in df.columns:
            df["hour"] = pd.to_datetime(df["Stime"], format="%H:%M:%S").dt.hour
            hourly = df["hour"].value_counts().sort_index()
            peak_hour = hourly.idxmax()
            print(f"\n--- 时间分布 ---")
            print(f"  出行高峰时段: {peak_hour}:00")
            print(f"  高峰小时出行量: {hourly.max():,}")

        print("=" * 60)

        self.cleaned_stats = {
            "total_trips": total_trips,
            "total_vehicles": total_vehicles,
            "avg_trips_per_vehicle": total_trips / total_vehicles if total_vehicles > 0 else 0,
        }

        return self.cleaned_stats

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------
    @staticmethod
    def _detect_encoding(filepath: str) -> str:
        """自动检测CSV文件编码"""
        # 尝试常见的中文编码
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin1"]
        for enc in encodings:
            try:
                pd.read_csv(filepath, encoding=enc, nrows=5)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return "utf-8"  # 默认回退

    def get_basic_info(self) -> dict:
        """获取数据集基本信息"""
        return {
            "raw_data_path": RAW_DATA_PATH,
            "cleaned_data_path": CLEANED_DATA_PATH,
            "raw_stats": self.raw_stats,
            "cleaned_stats": self.cleaned_stats,
        }
