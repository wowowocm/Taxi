# -*- coding: utf-8 -*-
"""
行程提取模块 (独立版本)
当数据已经是GPS格式但需要单独提取行程时使用
支持PySpark大规模并行处理
"""

import time
import pandas as pd
import numpy as np
from typing import List, Dict


class TripExtractor:
    """行程提取器，从GPS轨迹点中提取载客出行OD"""

    def __init__(self, use_spark: bool = False):
        """
        Parameters
        ----------
        use_spark : bool
            是否使用PySpark进行大规模处理
        """
        self.use_spark = use_spark
        self.spark = None
        if use_spark:
            self._init_spark()

    def _init_spark(self):
        """初始化PySpark"""
        try:
            from pyspark.sql import SparkSession
            self.spark = SparkSession.builder \
                .appName("TripExtractor") \
                .master("local[*]") \
                .getOrCreate()
            print("[INFO] PySpark初始化成功")
        except ImportError:
            print("[WARN] PySpark未安装，回退到Pandas处理")
            self.use_spark = False

    def extract_from_gps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从GPS数据中提取行程OD

        算法说明:
          1. 按 VehicleNum 分组
          2. 每组内按 Stime 排序
          3. 检测 OpenStatus 的 1→0 切换(行程开始)和 0→1 切换(行程结束)
          4. 配对每个行程的起点和终点

        Parameters
        ----------
        df : pd.DataFrame
            GPS数据，含 VehicleNum, Stime, Lng, Lat, OpenStatus

        Returns
        -------
        pd.DataFrame
            行程OD数据
        """
        if self.use_spark and self.spark is not None:
            return self._extract_with_spark(df)
        else:
            return self._extract_with_pandas(df)

    def _extract_with_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        使用Pandas提取行程OD

        内存友好实现：逐车辆处理，避免全量数据膨胀
        """
        print("[INFO] 使用Pandas提取行程...")
        start_time = time.time()

        all_trips = []
        total_vehicles = df["VehicleNum"].nunique()
        skipped_total = 0

        for idx, (vehicle, group) in enumerate(df.groupby("VehicleNum")):
            # 按时间排序
            group = group.sort_values("Stime").reset_index(drop=True)

            status = group["OpenStatus"].values
            times = group["Stime"].values
            lngs = group["Lng"].values
            lats = group["Lat"].values

            # 寻找状态切换点
            trip_starts = []
            trip_ends = []

            for i in range(1, len(status)):
                if status[i-1] == 1 and status[i] == 0:
                    trip_starts.append(i)
                elif status[i-1] == 0 and status[i] == 1:
                    trip_ends.append(i)

            # 配对行程起止
            end_ptr = 0
            for start_i in trip_starts:
                while end_ptr < len(trip_ends) and trip_ends[end_ptr] <= start_i:
                    end_ptr += 1
                if end_ptr < len(trip_ends):
                    end_i = trip_ends[end_ptr]
                    all_trips.append({
                        "VehicleNum": vehicle,
                        "Stime": times[start_i],
                        "SLng": lngs[start_i],
                        "SLat": lats[start_i],
                        "ELng": lngs[end_i],
                        "ELat": lats[end_i],
                        "Etime": times[end_i],
                    })
                    end_ptr += 1
                else:
                    skipped_total += 1

            # 进度报告
            if (idx + 1) % 50 == 0:
                print(f"  处理进度: {idx+1}/{total_vehicles} 辆车...")

        trips_df = pd.DataFrame(all_trips)
        elapsed = time.time() - start_time

        print(f"[INFO] 行程提取完成!")
        print(f"  车辆数: {total_vehicles}")
        print(f"  提取行程: {len(trips_df):,}")
        print(f"  丢弃未闭合: {skipped_total:,}")
        print(f"  耗时: {elapsed:.2f}秒")

        return trips_df

    def _extract_with_spark(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        使用PySpark提取行程OD (适用于超大规模数据)
        """
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        print("[INFO] 使用PySpark提取行程...")
        start_time = time.time()

        # 转换为Spark DataFrame
        sdf = self.spark.createDataFrame(df)

        # 按车辆和时间窗口处理
        window_spec = Window.partitionBy("VehicleNum").orderBy("Stime")

        # 标记状态切换
        sdf = sdf.withColumn("prev_status", F.lag("OpenStatus").over(window_spec))
        sdf = sdf.withColumn("status_change",
            F.when((F.col("prev_status") == 1) & (F.col("OpenStatus") == 0), "start")
             .when((F.col("prev_status") == 0) & (F.col("OpenStatus") == 1), "end")
        )

        # 过滤状态切换点
        changes = sdf.filter(F.col("status_change").isNotNull())

        # 转回Pandas做配对（简单场景下更灵活）
        changes_pd = changes.toPandas()

        elapsed = time.time() - start_time
        print(f"[INFO] PySpark行程提取完成! 耗时: {elapsed:.2f}秒")

        return self._pair_trips(changes_pd)

    def _pair_trips(self, changes_df: pd.DataFrame) -> pd.DataFrame:
        """配对行程起止点"""
        trips = []

        for vehicle, group in changes_df.groupby("VehicleNum"):
            group = group.sort_values("Stime")
            starts = group[group["status_change"] == "start"]
            ends = group[group["status_change"] == "end"]

            end_list = ends.to_dict("records")
            end_ptr = 0

            for _, start in starts.iterrows():
                while (end_ptr < len(end_list) and
                       end_list[end_ptr]["Stime"] <= start["Stime"]):
                    end_ptr += 1
                if end_ptr < len(end_list):
                    end_row = end_list[end_ptr]
                    trips.append({
                        "VehicleNum": vehicle,
                        "Stime": start["Stime"],
                        "SLng": start["Lng"],
                        "SLat": start["Lat"],
                        "ELng": end_row["Lng"],
                        "ELat": end_row["Lat"],
                        "Etime": end_row["Stime"],
                    })
                    end_ptr += 1

        return pd.DataFrame(trips)
