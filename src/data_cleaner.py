# -*- coding: utf-8 -*-
"""
数据清洗模块
实现5条核心清洗规则:
  规则1: 异常坐标过滤
  规则2: 异常速度处理
  规则3: 载客行程切片
  规则4: 行程OD提取
  规则5: 异常行程过滤

支持双模式:
  - Pandas 模式 (默认): 纯 Pandas 处理, 适用于中小规模数据
  - PySpark 模式: 利用 CentOS VM Spark 集群或本机多核并行处理, 适用于大规模数据
"""

import time
import pandas as pd
import numpy as np
from .config import (
    SHENZHEN_LNG_MIN, SHENZHEN_LNG_MAX,
    SHENZHEN_LAT_MIN, SHENZHEN_LAT_MAX,
    SPEED_MIN, SPEED_MAX,
    TRIP_DURATION_MIN, TRIP_DURATION_MAX,
    TRIP_DISTANCE_MIN, TRIP_AVG_SPEED_MIN, TRIP_AVG_SPEED_MAX,
)
from .logger import get_logger


class DataCleaner:
    """数据清洗流水线 (Pandas + PySpark 双模式)"""

    def __init__(self, use_spark: bool = False):
        """
        Parameters
        ----------
        use_spark : bool
            是否使用 PySpark 进行数据处理。
            True 时自动连接 Spark 集群 (远程VM优先→本机→回退Pandas)
        """
        self.cleaning_log = []   # 清洗日志
        self.stats = {}           # 各步骤统计
        self.use_spark = use_spark
        self.spark = None         # 延迟初始化

    def _get_spark(self):
        """延迟初始化 Spark 会话"""
        if self.spark is None and self.use_spark:
            from .spark_manager import get_spark
            self.spark = get_spark()
            if self.spark is None:
                log = get_logger()
                log.warning("PySpark 不可用，回退到 Pandas 模式")
                self.use_spark = False
        return self.spark

    # ==============================================================
    # 规则1: 异常坐标过滤
    # ==============================================================

    def filter_abnormal_coords(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤超出深圳市地理范围的 GPS 坐标 (Pandas 版本)

        过滤条件:
          Lng < 113.5 OR Lng > 114.5 OR Lat < 22.4 OR Lat > 22.9
        """
        before = len(df)
        print(f"\n[规则1] 异常坐标过滤...")
        print(f"  深圳范围: Lng[{SHENZHEN_LNG_MIN}, {SHENZHEN_LNG_MAX}], "
              f"Lat[{SHENZHEN_LAT_MIN}, {SHENZHEN_LAT_MAX}]")

        abnormal = (
            (df["Lng"] < SHENZHEN_LNG_MIN) |
            (df["Lng"] > SHENZHEN_LNG_MAX) |
            (df["Lat"] < SHENZHEN_LAT_MIN) |
            (df["Lat"] > SHENZHEN_LAT_MAX)
        )
        df_clean = df[~abnormal].copy()
        removed = before - len(df_clean)

        print(f"  过滤前: {before:,} 条")
        print(f"  过滤后: {len(df_clean):,} 条")
        print(f"  剔除: {removed:,} 条 ({removed/before*100:.2f}%)")

        self._log_step("规则1-异常坐标过滤", before, len(df_clean), removed)
        return df_clean

    def _spark_filter_abnormal_coords(self, sdf):
        """
        规则1 PySpark 版本: 过滤异常坐标
        返回: (SparkDataFrame, before_count, after_count)
        """
        from pyspark.sql import functions as F

        before = sdf.count()
        print(f"\n[规则1|PySpark] 异常坐标过滤...")
        print(f"  深圳范围: Lng[{SHENZHEN_LNG_MIN}, {SHENZHEN_LNG_MAX}], "
              f"Lat[{SHENZHEN_LAT_MIN}, {SHENZHEN_LAT_MAX}]")

        sdf_clean = sdf.filter(
            (F.col("Lng") >= SHENZHEN_LNG_MIN) &
            (F.col("Lng") <= SHENZHEN_LNG_MAX) &
            (F.col("Lat") >= SHENZHEN_LAT_MIN) &
            (F.col("Lat") <= SHENZHEN_LAT_MAX)
        )
        after = sdf_clean.count()
        removed = before - after

        print(f"  过滤前: {before:,} 条")
        print(f"  过滤后: {after:,} 条")
        print(f"  剔除: {removed:,} 条 ({removed/before*100:.2f}%)")

        self._log_step("规则1-异常坐标过滤(PySpark)", before, after, removed)
        return sdf_clean

    # ==============================================================
    # 规则2: 异常速度处理
    # ==============================================================

    def handle_abnormal_speed(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理不合理速度值 (Pandas 版本)

        Speed < 0 或 Speed > 150 → 标记并线性插值填充
        """
        before = len(df)
        print(f"\n[规则2] 异常速度处理...")
        print(f"  合理范围: [{SPEED_MIN}, {SPEED_MAX}] km/h")

        abnormal_speed = (df["Speed"] < SPEED_MIN) | (df["Speed"] > SPEED_MAX)
        abnormal_count = abnormal_speed.sum()
        print(f"  异常速度记录: {abnormal_count:,} 条 ({abnormal_count/before*100:.2f}%)")

        df_clean = df.copy()
        df_clean.loc[abnormal_speed, "Speed"] = np.nan

        df_clean["Speed"] = df_clean.groupby("VehicleNum")["Speed"].transform(
            lambda x: x.interpolate(method="linear", limit_direction="both")
        )

        still_nan = df_clean["Speed"].isna().sum()
        if still_nan > 0:
            print(f"  仍有 {still_nan} 条无法插值，予以剔除")
            df_clean = df_clean.dropna(subset=["Speed"])

        removed = before - len(df_clean)
        print(f"  处理后: {len(df_clean):,} 条")

        self._log_step("规则2-异常速度处理", before, len(df_clean), removed)
        return df_clean

    def _spark_handle_abnormal_speed(self, sdf):
        """
        规则2 PySpark 版本: 异常速度插值

        使用 Window 函数按车辆分组，对异常速度执行前向/后向填充
        """
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        before = sdf.count()
        print(f"\n[规则2|PySpark] 异常速度处理...")
        print(f"  合理范围: [{SPEED_MIN}, {SPEED_MAX}] km/h")

        # 标记异常速度 (设为 null)
        sdf = sdf.withColumn(
            "Speed",
            F.when(
                (F.col("Speed") >= SPEED_MIN) & (F.col("Speed") <= SPEED_MAX),
                F.col("Speed")
            ).otherwise(None)
        )

        abn_count = sdf.filter(F.col("Speed").isNull()).count()
        print(f"  异常速度记录: {abn_count:,} 条 ({abn_count/before*100:.2f}%)")

        # 按车辆分组，时间排序
        window_spec = Window.partitionBy("VehicleNum").orderBy("Stime")

        # 前向填充 (用上一个有效值)
        sdf = sdf.withColumn("Speed_fwd", F.last("Speed", ignorenulls=True).over(window_spec))

        # 后向窗口
        window_rev = Window.partitionBy("VehicleNum").orderBy(F.col("Stime").desc())
        sdf = sdf.withColumn("Speed_rev", F.last("Speed", ignorenulls=True).over(window_rev))

        # 合并: 优先前向填充，否则后向填充
        sdf = sdf.withColumn(
            "Speed",
            F.coalesce(F.col("Speed"), F.col("Speed_fwd"), F.col("Speed_rev"))
        ).drop("Speed_fwd", "Speed_rev")

        # 剔除仍然为 null 的记录
        still_null = sdf.filter(F.col("Speed").isNull()).count()
        if still_null > 0:
            print(f"  仍有 {still_null} 条无法插值，予以剔除")
            sdf = sdf.filter(F.col("Speed").isNotNull())

        after = sdf.count()
        removed = before - after
        print(f"  处理后: {after:,} 条")

        self._log_step("规则2-异常速度处理(PySpark)", before, after, removed)
        return sdf

    # ==============================================================
    # 规则3 & 4: 载客行程切片 + OD提取
    # ==============================================================

    def extract_trips(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从 GPS 点序列中提取载客行程的 OD 信息 (Pandas 版本)

        核心逻辑:
          按车辆分组 → 识别 OpenStatus 从 1→0 切换(行程开始)
          → 从 0→1 切换(行程结束) → 提取起止点信息
        """
        print(f"\n[规则3&4] 载客行程切片与OD提取...")
        start_time = time.time()

        trips = []
        skipped = 0

        for vehicle, group in df.groupby("VehicleNum"):
            group = group.sort_values("Stime")
            status = group["OpenStatus"].values
            times = group["Stime"].values
            lngs = group["Lng"].values
            lats = group["Lat"].values

            trip_start_idx = []
            trip_end_idx = []

            for i in range(1, len(status)):
                if status[i-1] == 1 and status[i] == 0:
                    trip_start_idx.append(i)
                elif status[i-1] == 0 and status[i] == 1:
                    trip_end_idx.append(i)

            end_ptr = 0
            for start_i in trip_start_idx:
                while end_ptr < len(trip_end_idx) and trip_end_idx[end_ptr] <= start_i:
                    end_ptr += 1
                if end_ptr < len(trip_end_idx):
                    end_i = trip_end_idx[end_ptr]
                    trips.append({
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
                    skipped += 1

        trips_df = pd.DataFrame(trips)
        elapsed = time.time() - start_time
        print(f"  提取行程数: {len(trips_df):,}")
        print(f"  丢弃未闭合行程: {skipped:,}")
        print(f"  耗时: {elapsed:.2f}秒")

        self._log_step("规则3&4-行程切片与OD提取",
                       before=len(df), after=len(trips_df),
                       removed=len(df) - len(trips_df))
        return trips_df

    def _spark_extract_trips(self, sdf):
        """
        规则3&4 PySpark 版本: 行程切片与 OD 提取

        算法:
          1. 按 VehicleNum 分组, 按 Stime 排序
          2. 使用 lag 窗口函数检测 OpenStatus 切换 (1→0 = 行程开始, 0→1 = 行程结束)
          3. 配对每个 start 与其后第一个 end
        """
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        before = sdf.count()
        print(f"\n[规则3&4|PySpark] 载客行程切片与OD提取...")
        start_time = time.time()

        # Window: 按车辆分组，按时间排序
        window_spec = Window.partitionBy("VehicleNum").orderBy("Stime")

        # 使用 lag 获取前一状态
        sdf = sdf.withColumn("prev_status", F.lag("OpenStatus").over(window_spec))

        # 标记状态切换: 1→0 = 开始, 0→1 = 结束
        sdf = sdf.withColumn(
            "transition",
            F.when((F.col("prev_status") == 1) & (F.col("OpenStatus") == 0), "start")
             .when((F.col("prev_status") == 0) & (F.col("OpenStatus") == 1), "end")
             .otherwise(None)
        )

        # 只保留切换点
        transitions = sdf.filter(F.col("transition").isNotNull())

        # 转换为 Pandas 进行配对 (数据量已大幅减少, 只有切换点)
        transitions_pd = transitions.select(
            "VehicleNum", "Stime", "Lng", "Lat", "transition"
        ).toPandas()

        # 配对逻辑 (与 Pandas 版本相同)
        trips = []
        skipped = 0

        for vehicle, group in transitions_pd.groupby("VehicleNum"):
            group = group.sort_values("Stime")
            starts = group[group["transition"] == "start"]
            ends = group[group["transition"] == "end"]

            end_list = ends.to_dict("records")
            end_ptr = 0

            for _, start_row in starts.iterrows():
                while (end_ptr < len(end_list) and
                       end_list[end_ptr]["Stime"] <= start_row["Stime"]):
                    end_ptr += 1
                if end_ptr < len(end_list):
                    end_rec = end_list[end_ptr]
                    trips.append({
                        "VehicleNum": vehicle,
                        "Stime": start_row["Stime"],
                        "SLng": start_row["Lng"],
                        "SLat": start_row["Lat"],
                        "ELng": end_rec["Lng"],
                        "ELat": end_rec["Lat"],
                        "Etime": end_rec["Stime"],
                    })
                    end_ptr += 1
                else:
                    skipped += 1

        trips_df = pd.DataFrame(trips)
        elapsed = time.time() - start_time
        print(f"  提取行程数: {len(trips_df):,}")
        print(f"  丢弃未闭合行程: {skipped:,}")
        print(f"  耗时: {elapsed:.2f}秒")

        self._log_step("规则3&4-行程切片与OD提取(PySpark)",
                       before=before, after=len(trips_df),
                       removed=before - len(trips_df))
        return trips_df

    # ==============================================================
    # 规则5: 异常行程过滤
    # ==============================================================

    def filter_abnormal_trips(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤不合理行程 (Pandas 版本)

        过滤条件:
          - 行程时长 < 1分钟 或 > 4小时
          - 行程距离 < 200米
          - 平均速度不在 5-100 km/h 范围内
        """
        before = len(df)
        print(f"\n[规则5] 异常行程过滤...")

        df = df.copy()

        df["stime_dt"] = pd.to_datetime(df["Stime"], format="%H:%M:%S")
        df["etime_dt"] = pd.to_datetime(df["Etime"], format="%H:%M:%S")

        mask_cross_day = df["etime_dt"] < df["stime_dt"]
        df.loc[mask_cross_day, "etime_dt"] += pd.Timedelta(days=1)

        df["duration_min"] = (
            (df["etime_dt"] - df["stime_dt"]).dt.total_seconds() / 60
        )

        df["distance_km"] = self._haversine_distance(
            df["SLng"], df["SLat"], df["ELng"], df["ELat"]
        )

        df["avg_speed"] = np.where(
            df["duration_min"] > 0,
            df["distance_km"] / (df["duration_min"] / 60),
            0
        )

        cond_duration_min = df["duration_min"] >= TRIP_DURATION_MIN
        cond_duration_max = df["duration_min"] <= TRIP_DURATION_MAX
        cond_distance = df["distance_km"] >= TRIP_DISTANCE_MIN
        cond_speed_min = df["avg_speed"] >= TRIP_AVG_SPEED_MIN
        cond_speed_max = df["avg_speed"] <= TRIP_AVG_SPEED_MAX

        print(f"  过滤条件:")
        print(f"    时长<{TRIP_DURATION_MIN}分钟: {(~cond_duration_min).sum():,}")
        print(f"    时长>{TRIP_DURATION_MAX}分钟: {(~cond_duration_max).sum():,}")
        print(f"    距离<{TRIP_DISTANCE_MIN}km: {(~cond_distance).sum():,}")
        print(f"    均速<{TRIP_AVG_SPEED_MIN}km/h: {(~cond_speed_min).sum():,}")
        print(f"    均速>{TRIP_AVG_SPEED_MAX}km/h: {(~cond_speed_max).sum():,}")

        valid = (cond_duration_min & cond_duration_max &
                 cond_distance & cond_speed_min & cond_speed_max)

        df_clean = df[valid].copy()

        keep_cols = ["VehicleNum", "Stime", "SLng", "SLat",
                     "ELng", "ELat", "Etime",
                     "duration_min", "distance_km", "avg_speed"]
        df_clean = df_clean[keep_cols].copy()

        removed = before - len(df_clean)
        print(f"  过滤前: {before:,} 条")
        print(f"  过滤后: {len(df_clean):,} 条")
        print(f"  剔除: {removed:,} 条 ({removed/before*100:.2f}%)")

        self._log_step("规则5-异常行程过滤", before, len(df_clean), removed)
        return df_clean

    def _spark_filter_abnormal_trips(self, trips_df: pd.DataFrame) -> pd.DataFrame:
        """
        规则5 PySpark 版本: 异常行程过滤

        参数为 Pandas DataFrame (来自 _spark_extract_trips),
        转换为 Spark 后执行距离计算和过滤, 然后返回 Pandas DataFrame
        """
        spark = self.spark
        from pyspark.sql import functions as F
        from pyspark.sql import types as T

        before = len(trips_df)
        print(f"\n[规则5|PySpark] 异常行程过滤...")

        # 将 Pandas 转为 Spark
        sdf = spark.createDataFrame(trips_df)

        # Haversine 距离 UDF
        @F.udf(T.DoubleType())
        def haversine_udf(lng1, lat1, lng2, lat2):
            if any(v is None for v in (lng1, lat1, lng2, lat2)):
                return 0.0
            R = 6371.0
            lng1_r = np.radians(float(lng1))
            lat1_r = np.radians(float(lat1))
            lng2_r = np.radians(float(lng2))
            lat2_r = np.radians(float(lat2))
            dlat = lat2_r - lat1_r
            dlng = lng2_r - lng1_r
            a = (np.sin(dlat / 2) ** 2 +
                 np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlng / 2) ** 2)
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
            return float(R * c)

        # 时间解析: 提取时分秒 → 计算秒数偏移
        sdf = sdf.withColumn("stime_sec",
            F.hour(F.to_timestamp(F.col("Stime"), "HH:mm:ss")) * 3600 +
            F.minute(F.to_timestamp(F.col("Stime"), "HH:mm:ss")) * 60 +
            F.second(F.to_timestamp(F.col("Stime"), "HH:mm:ss"))
        )
        sdf = sdf.withColumn("etime_sec",
            F.hour(F.to_timestamp(F.col("Etime"), "HH:mm:ss")) * 3600 +
            F.minute(F.to_timestamp(F.col("Etime"), "HH:mm:ss")) * 60 +
            F.second(F.to_timestamp(F.col("Etime"), "HH:mm:ss"))
        )

        # 处理跨日 (etime_sec < stime_sec → +86400)
        sdf = sdf.withColumn(
            "etime_sec",
            F.when(F.col("etime_sec") < F.col("stime_sec"),
                   F.col("etime_sec") + 86400).otherwise(F.col("etime_sec"))
        )

        # 计算 duration_min
        sdf = sdf.withColumn("duration_min", (F.col("etime_sec") - F.col("stime_sec")) / 60.0)

        # 计算 Haversine 距离
        sdf = sdf.withColumn(
            "distance_km",
            haversine_udf(F.col("SLng"), F.col("SLat"), F.col("ELng"), F.col("ELat"))
        )

        # 计算平均速度
        sdf = sdf.withColumn(
            "avg_speed",
            F.when(F.col("duration_min") > 0,
                   F.col("distance_km") / (F.col("duration_min") / 60.0)).otherwise(0.0)
        )

        # 统计过滤条件
        cond_dur_min = F.col("duration_min") >= TRIP_DURATION_MIN
        cond_dur_max = F.col("duration_min") <= TRIP_DURATION_MAX
        cond_dist = F.col("distance_km") >= TRIP_DISTANCE_MIN
        cond_speed_min = F.col("avg_speed") >= TRIP_AVG_SPEED_MIN
        cond_speed_max = F.col("avg_speed") <= TRIP_AVG_SPEED_MAX

        print(f"  过滤条件:")
        print(f"    时长<{TRIP_DURATION_MIN}分钟: {sdf.filter(~cond_dur_min).count():,}")
        print(f"    时长>{TRIP_DURATION_MAX}分钟: {sdf.filter(~cond_dur_max).count():,}")
        print(f"    距离<{TRIP_DISTANCE_MIN}km: {sdf.filter(~cond_dist).count():,}")
        print(f"    均速<{TRIP_AVG_SPEED_MIN}km/h: {sdf.filter(~cond_speed_min).count():,}")
        print(f"    均速>{TRIP_AVG_SPEED_MAX}km/h: {sdf.filter(~cond_speed_max).count():,}")

        # 应用综合过滤
        sdf_clean = sdf.filter(
            cond_dur_min & cond_dur_max & cond_dist & cond_speed_min & cond_speed_max
        )

        # 保留核心字段
        sdf_clean = sdf_clean.select(
            "VehicleNum", "Stime", "SLng", "SLat", "ELng", "ELat", "Etime",
            "duration_min", "distance_km", "avg_speed"
        )

        # 转回 Pandas
        df_clean = sdf_clean.toPandas()

        removed = before - len(df_clean)
        print(f"  过滤前: {before:,} 条")
        print(f"  过滤后: {len(df_clean):,} 条")
        print(f"  剔除: {removed:,} 条 ({removed/before*100:.2f}%)")

        self._log_step("规则5-异常行程过滤(PySpark)", before, len(df_clean), removed)
        return df_clean

    # ==============================================================
    # 完整清洗流水线
    # ==============================================================

    def run_pipeline(self, df: pd.DataFrame,
                     skip_to_od: bool = False) -> pd.DataFrame:
        """
        执行完整的数据清洗流水线

        根据 self.use_spark 自动选择 PySpark 或 Pandas 模式。
        两种模式返回相同格式的 Pandas DataFrame。

        Parameters
        ----------
        df : pd.DataFrame
            原始 GPS 数据 (含 VehicleNum, Stime, Lng, Lat, OpenStatus, Speed)
        skip_to_od : bool
            如果数据已经是 OD 格式，跳过 GPS→OD 转换步骤

        Returns
        -------
        pd.DataFrame
            清洗后的出行 OD 数据
        """
        print("\n" + "=" * 60)
        mode = "PySpark" if self.use_spark else "Pandas"
        print(f"  开始数据清洗流水线 ({mode} 模式)")
        print("=" * 60)
        log = get_logger()
        log.info(f"开始数据清洗流水线 ({mode} 模式)")
        total_start = time.time()

        if self.use_spark:
            # ---- PySpark 模式 ----
            spark = self._get_spark()
            if spark is None:
                # PySpark 不可用，自动切换到 Pandas
                self.use_spark = False
                log.warning("PySpark 初始化失败，回退到 Pandas 模式")
                return self.run_pipeline(df, skip_to_od)

            # 将 Pandas DataFrame 转为 Spark DataFrame
            sdf = spark.createDataFrame(df)
            log.info(f"数据已加载到 PySpark: {sdf.count():,} 行")

            if not skip_to_od:
                # 规则1: 异常坐标过滤
                sdf = self._spark_filter_abnormal_coords(sdf)
                # 规则2: 异常速度处理
                sdf = self._spark_handle_abnormal_speed(sdf)
                # 规则3&4: 行程切片与OD提取 (转回 Pandas 做配对)
                current = self._spark_extract_trips(sdf)
            else:
                current = df.copy()
                log.info("跳过GPS→OD转换，直接进行行程过滤")

            # 规则5: 异常行程过滤 (PySpark 版本)
            current = self._spark_filter_abnormal_trips(current)

        else:
            # ---- Pandas 模式 (原逻辑) ----
            current = df.copy()

            if not skip_to_od:
                current = self.filter_abnormal_coords(current)
                current = self.handle_abnormal_speed(current)
                current = self.extract_trips(current)
            else:
                log.info("跳过GPS→OD转换，直接进行行程过滤")

            current = self.filter_abnormal_trips(current)

        total_elapsed = time.time() - total_start
        log.info(f"清洗流水线总耗时: {total_elapsed:.2f}秒")
        log.info(f"最终输出: {len(current):,} 条有效行程记录")
        log.info(f"输出字段: {list(current.columns)}")

        return current

    # ==============================================================
    # 导出
    # ==============================================================

    def export_cleaned_data(self, df: pd.DataFrame, filepath: str) -> None:
        """导出清洗后的数据为 CSV 文件 (UTF-8 with BOM, 兼容 Excel)"""
        log = get_logger()
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        log.info(f"清洗数据已导出至: {filepath} (共 {len(df):,} 条)")

    def export_to_mysql(self, df: pd.DataFrame) -> bool:
        """
        将清洗后的 OD 数据上传到 MySQL 数据库 (CentOS VM)

        Parameters
        ----------
        df : pd.DataFrame
            清洗后的 OD 数据

        Returns
        -------
        bool
            是否上传成功
        """
        log = get_logger()
        try:
            from .mysql_uploader import MySQLUploader
            uploader = MySQLUploader()
            uploader.upload_od_trips(df)
            log.info(f"OD数据已上传至MySQL: {len(df):,} 条")
            return True
        except Exception as e:
            log.error(f"MySQL上传失败: {e}")
            return False

    # ==============================================================
    # 辅助方法
    # ==============================================================

    @staticmethod
    def _haversine_distance(lng1, lat1, lng2, lat2):
        """Haversine 公式计算两点间距离（公里）"""
        R = 6371.0
        lng1_r = np.radians(lng1)
        lat1_r = np.radians(lat1)
        lng2_r = np.radians(lng2)
        lat2_r = np.radians(lat2)
        dlat = lat2_r - lat1_r
        dlng = lng2_r - lng1_r
        a = (np.sin(dlat / 2) ** 2 +
             np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlng / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    def _log_step(self, step_name: str, before: int, after: int,
                  removed: int) -> None:
        """记录清洗步骤"""
        record = {
            "step": step_name,
            "before": before,
            "after": after,
            "removed": removed,
            "removal_rate": removed / before * 100 if before > 0 else 0,
        }
        self.cleaning_log.append(record)
        self.stats[step_name] = record

    def get_cleaning_report(self) -> str:
        """生成清洗报告"""
        lines = ["\n数据清洗报告", "=" * 50]
        for log_item in self.cleaning_log:
            lines.append(
                f"  {log_item['step']}: {log_item['before']:,} → {log_item['after']:,} "
                f"(剔除 {log_item['removed']:,}, {log_item['removal_rate']:.2f}%)"
            )
        return "\n".join(lines)
