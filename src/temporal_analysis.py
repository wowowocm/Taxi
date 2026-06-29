# -*- coding: utf-8 -*-
"""
时序分析模块 (支持 Pandas + PySpark 双模式)
功能:
  1. 小时级出行量分布统计
  2. 出行高峰自动识别
  3. 载客率时间变化分析
  4. 平均行程时长随时间变化
  5. 出行时长/距离分布统计
"""

import pandas as pd
import numpy as np
from .config import TIME_PERIODS, HOUR_LABELS


class TemporalAnalyzer:
    """时序分析器 (Pandas + PySpark 双模式)"""

    def __init__(self, df: pd.DataFrame = None, use_spark: bool = False):
        """
        Parameters
        ----------
        df : pd.DataFrame
            清洗后的 OD 数据 (含 VehicleNum, Stime, SLng, SLat, ELng, ELat, Etime)
        use_spark : bool
            是否使用 PySpark 进行分析
        """
        self.df = df.copy() if df is not None else None
        self.hourly_stats = None
        self.peak_info = None
        self._preprocessed = False
        self.use_spark = use_spark
        self.spark = None  # 延迟初始化

        if self.df is not None:
            self._preprocess()

    def _get_spark(self):
        """延迟初始化 Spark 会话"""
        if self.spark is None and self.use_spark:
            from .spark_manager import get_spark
            self.spark = get_spark()
            if self.spark is None:
                self.use_spark = False
        return self.spark

    def load_data(self, df: pd.DataFrame):
        """加载 OD 数据并自动预处理"""
        self.df = df.copy()
        self._preprocessed = False
        self.hourly_stats = None
        self.peak_info = None
        self._preprocess()

    def _preprocess(self):
        """数据预处理：添加时间相关字段"""
        if self.df is None:
            raise ValueError("请先加载数据")
        if self._preprocessed:
            return

        self.df["stime_dt"] = pd.to_datetime(self.df["Stime"], format="%H:%M:%S")
        self.df["etime_dt"] = pd.to_datetime(self.df["Etime"], format="%H:%M:%S")

        mask = self.df["etime_dt"] < self.df["stime_dt"]
        self.df.loc[mask, "etime_dt"] += pd.Timedelta(days=1)

        self.df["hour"] = self.df["stime_dt"].dt.hour

        if "duration_min" not in self.df.columns:
            self.df["duration_min"] = (
                (self.df["etime_dt"] - self.df["stime_dt"]).dt.total_seconds() / 60
            )

        if "distance_km" not in self.df.columns:
            self.df["distance_km"] = self._approx_distance(
                self.df["SLng"], self.df["SLat"],
                self.df["ELng"], self.df["ELat"]
            )

        self._preprocessed = True

    # ----------------------------------------------------------
    # 小时出行量分布
    # ----------------------------------------------------------

    def hourly_trip_count(self) -> pd.DataFrame:
        """
        按小时统计出行量分布

        Returns
        -------
        pd.DataFrame
            含 hour, trip_count, avg_duration, avg_distance 等列
        """
        if self.df is None:
            raise ValueError("请先加载数据")

        if self.use_spark and self._get_spark() is not None:
            return self._spark_hourly_trip_count()

        grouped = self.df.groupby("hour").agg(
            trip_count=("VehicleNum", "count"),
            avg_duration=("duration_min", "mean"),
            median_duration=("duration_min", "median"),
            avg_distance=("distance_km", "mean"),
            unique_vehicles=("VehicleNum", "nunique"),
        ).reset_index()

        all_hours = pd.DataFrame({"hour": range(24)})
        grouped = all_hours.merge(grouped, on="hour", how="left").fillna(0)
        self.hourly_stats = grouped
        return grouped

    def _spark_hourly_trip_count(self) -> pd.DataFrame:
        """PySpark 版本: 按小时统计"""
        from pyspark.sql import functions as F

        spark = self.spark
        sdf = spark.createDataFrame(self.df)

        grouped = sdf.groupBy("hour").agg(
            F.count("VehicleNum").alias("trip_count"),
            F.mean("duration_min").alias("avg_duration"),
            F.expr("percentile_approx(duration_min, 0.5)").alias("median_duration"),
            F.mean("distance_km").alias("avg_distance"),
            F.countDistinct("VehicleNum").alias("unique_vehicles"),
        ).toPandas()

        all_hours = pd.DataFrame({"hour": range(24)})
        grouped = all_hours.merge(grouped, on="hour", how="left").fillna(0)
        self.hourly_stats = grouped
        return grouped

    # ----------------------------------------------------------
    # 高峰识别
    # ----------------------------------------------------------

    def identify_peak_hours(self) -> dict:
        """自动识别出行高峰时段 (出行量 > 日均1.5倍)"""
        if self.hourly_stats is None:
            self.hourly_trip_count()

        mean_hourly = self.hourly_stats["trip_count"].mean()
        threshold = mean_hourly * 1.5

        peak_mask = self.hourly_stats["trip_count"] > threshold
        peak_hours = self.hourly_stats.loc[peak_mask, "hour"].tolist()

        morning_peak = [h for h in peak_hours if 6 <= h <= 10]
        evening_peak = [h for h in peak_hours if 16 <= h <= 20]

        self.peak_info = {
            "mean_hourly_trips": mean_hourly,
            "peak_threshold": threshold,
            "peak_hours": peak_hours,
            "morning_peak": morning_peak,
            "evening_peak": evening_peak,
            "peak_hour_max": int(self.hourly_stats.loc[
                self.hourly_stats["trip_count"].idxmax(), "hour"
            ]),
            "peak_max_trips": int(self.hourly_stats["trip_count"].max()),
        }

        print("\n--- 出行高峰识别 ---")
        print(f"  日均小时出行量: {mean_hourly:.0f}")
        print(f"  高峰阈值 (1.5x): {threshold:.0f}")
        if morning_peak:
            print(f"  早高峰: {morning_peak[0]}:00-{morning_peak[-1]+1}:00")
        if evening_peak:
            print(f"  晚高峰: {evening_peak[0]}:00-{evening_peak[-1]+1}:00")
        print(f"  最高峰小时: {self.peak_info['peak_hour_max']}:00 "
              f"({self.peak_info['peak_max_trips']:,}次)")

        return self.peak_info

    # ----------------------------------------------------------
    # 时段分析
    # ----------------------------------------------------------

    def period_analysis(self) -> pd.DataFrame:
        """按时段统计出行特征"""
        if self.df is None:
            raise ValueError("请先加载数据")

        results = []
        for period_name, (start, end) in TIME_PERIODS.items():
            mask = (self.df["Stime"] >= start) & (self.df["Stime"] < end)
            period_df = self.df[mask]

            results.append({
                "时段": period_name,
                "时间范围": f"{start}-{end}",
                "出行量": len(period_df),
                "占比(%)": len(period_df) / len(self.df) * 100,
                "平均时长(分钟)": period_df["duration_min"].mean(),
                "平均距离(km)": period_df["distance_km"].mean(),
                "活跃车辆数": period_df["VehicleNum"].nunique(),
            })

        return pd.DataFrame(results)

    # ----------------------------------------------------------
    # 行程时长/距离分布
    # ----------------------------------------------------------

    def duration_distribution(self) -> dict:
        """行程时长分布统计"""
        if self.df is None:
            raise ValueError("请先加载数据")

        dur = self.df["duration_min"]

        dur_bins = [0, 5, 10, 20, 30, 60, 120, 240]
        dur_labels = ["≤5分钟", "5-10分钟", "10-20分钟", "20-30分钟",
                      "30-60分钟", "60-120分钟", ">120分钟"]
        dur_seg = pd.cut(dur, bins=dur_bins, labels=dur_labels, right=True)

        stats = {
            "mean": dur.mean(),
            "median": dur.median(),
            "std": dur.std(),
            "skewness": dur.skew(),
            "kurtosis": dur.kurtosis(),
            "percentiles": {
                "25%": dur.quantile(0.25),
                "50%": dur.quantile(0.50),
                "75%": dur.quantile(0.75),
                "90%": dur.quantile(0.90),
                "95%": dur.quantile(0.95),
                "99%": dur.quantile(0.99),
            },
            "segments": dur_seg.value_counts().to_dict(),
            "min": dur.min(),
            "max": dur.max(),
        }

        print("\n--- 行程时长分布 ---")
        print(f"  均值: {stats['mean']:.1f}分钟")
        print(f"  中位数: {stats['median']:.1f}分钟")
        print(f"  标准差: {stats['std']:.1f}分钟")
        print(f"  90%分位: {stats['percentiles']['90%']:.1f}分钟")

        return stats

    def distance_distribution(self) -> dict:
        """行程距离分布统计"""
        if self.df is None:
            raise ValueError("请先加载数据")

        dist = self.df["distance_km"]

        stats = {
            "mean": dist.mean(),
            "median": dist.median(),
            "std": dist.std(),
            "short_trip_ratio": (dist < 3).mean() * 100,
            "long_trip_ratio": (dist > 10).mean() * 100,
            "percentiles": {
                "25%": dist.quantile(0.25),
                "50%": dist.quantile(0.50),
                "75%": dist.quantile(0.75),
                "90%": dist.quantile(0.90),
                "95%": dist.quantile(0.95),
            },
        }

        print("\n--- 行程距离分布 ---")
        print(f"  均值: {stats['mean']:.2f}km")
        print(f"  中位数: {stats['median']:.2f}km")
        print(f"  短途(<3km)占比: {stats['short_trip_ratio']:.1f}%")
        print(f"  长途(>10km)占比: {stats['long_trip_ratio']:.1f}%")

        return stats

    # ----------------------------------------------------------
    # 车辆运营效率
    # ----------------------------------------------------------

    def vehicle_efficiency(self) -> pd.DataFrame:
        """计算每辆车的运营效率指标"""
        if self.df is None:
            raise ValueError("请先加载数据")

        if self.use_spark and self._get_spark() is not None:
            return self._spark_vehicle_efficiency()

        efficiency = self.df.groupby("VehicleNum").agg(
            trip_count=("duration_min", "count"),
            total_duration=("duration_min", "sum"),
            total_distance=("distance_km", "sum"),
            avg_duration=("duration_min", "mean"),
            avg_distance=("distance_km", "mean"),
            first_trip=("Stime", "min"),
            last_trip=("Etime", "max"),
        ).reset_index()

        efficiency = efficiency.sort_values("trip_count", ascending=False)

        print("\n--- 车辆运营效率 Top-10 ---")
        print(efficiency.head(10).to_string(index=False))

        return efficiency

    def _spark_vehicle_efficiency(self) -> pd.DataFrame:
        """PySpark 版本: 车辆运营效率"""
        from pyspark.sql import functions as F

        spark = self.spark
        sdf = spark.createDataFrame(self.df)

        efficiency = sdf.groupBy("VehicleNum").agg(
            F.count("duration_min").alias("trip_count"),
            F.sum("duration_min").alias("total_duration"),
            F.sum("distance_km").alias("total_distance"),
            F.mean("duration_min").alias("avg_duration"),
            F.mean("distance_km").alias("avg_distance"),
            F.min("Stime").alias("first_trip"),
            F.max("Etime").alias("last_trip"),
        ).orderBy(F.desc("trip_count")).toPandas()

        print("\n--- 车辆运营效率 Top-10 (PySpark) ---")
        print(efficiency.head(10).to_string(index=False))

        return efficiency

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    @staticmethod
    def _approx_distance(lng1, lat1, lng2, lat2):
        """简化的距离计算（等矩形近似）"""
        R = 6371.0
        lat_mid = np.radians((lat1 + lat2) / 2)
        dx = (lng2 - lng1) * np.cos(lat_mid) * (np.pi / 180) * R
        dy = (lat2 - lat1) * (np.pi / 180) * R
        return np.sqrt(dx**2 + dy**2)

    def get_summary(self) -> dict:
        """获取时序分析摘要"""
        if self.hourly_stats is None:
            self.hourly_trip_count()
        if self.peak_info is None:
            self.identify_peak_hours()

        return {
            "total_trips": len(self.df),
            "total_vehicles": self.df["VehicleNum"].nunique(),
            "peak_morning": self.peak_info.get("morning_peak", []),
            "peak_evening": self.peak_info.get("evening_peak", []),
            "peak_hour_max": self.peak_info.get("peak_hour_max"),
        }
