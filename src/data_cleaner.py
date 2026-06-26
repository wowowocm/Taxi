# -*- coding: utf-8 -*-
"""
数据清洗模块
实现5条核心清洗规则:
  规则1: 异常坐标过滤
  规则2: 异常速度处理
  规则3: 载客行程切片
  规则4: 行程OD提取
  规则5: 异常行程过滤
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


class DataCleaner:
    """数据清洗流水线"""

    def __init__(self):
        self.cleaning_log = []   # 清洗日志
        self.stats = {}           # 各步骤统计

    # ----------------------------------------------------------
    # 规则1: 异常坐标过滤
    # ----------------------------------------------------------
    def filter_abnormal_coords(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤超出深圳市地理范围的GPS坐标

        过滤条件:
          Lng < 113.5 OR Lng > 114.5 OR Lat < 22.4 OR Lat > 22.9

        Parameters
        ----------
        df : pd.DataFrame
            原始GPS数据

        Returns
        -------
        pd.DataFrame
            过滤后的数据
        """
        before = len(df)
        print(f"\n[规则1] 异常坐标过滤...")
        print(f"  深圳范围: Lng[{SHENZHEN_LNG_MIN}, {SHENZHEN_LNG_MAX}], "
              f"Lat[{SHENZHEN_LAT_MIN}, {SHENZHEN_LAT_MAX}]")

        # 标记异常坐标
        abnormal = (
            (df["Lng"] < SHENZHEN_LNG_MIN) |
            (df["Lng"] > SHENZHEN_LNG_MAX) |
            (df["Lat"] < SHENZHEN_LAT_MIN) |
            (df["Lat"] > SHENZHEN_LAT_MAX)
        )

        # 过滤
        df_clean = df[~abnormal].copy()
        removed = before - len(df_clean)

        print(f"  过滤前: {before:,} 条")
        print(f"  过滤后: {len(df_clean):,} 条")
        print(f"  剔除: {removed:,} 条 ({removed/before*100:.2f}%)")

        self._log_step("规则1-异常坐标过滤", before, len(df_clean), removed)
        return df_clean

    # ----------------------------------------------------------
    # 规则2: 异常速度处理
    # ----------------------------------------------------------
    def handle_abnormal_speed(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理不合理速度值

        处理方式:
          Speed < 0 或 Speed > 150 → 标记并线性插值填充

        Parameters
        ----------
        df : pd.DataFrame
            经规则1处理后的数据

        Returns
        -------
        pd.DataFrame
        """
        before = len(df)
        print(f"\n[规则2] 异常速度处理...")
        print(f"  合理范围: [{SPEED_MIN}, {SPEED_MAX}] km/h")

        # 标记异常速度
        abnormal_speed = (df["Speed"] < SPEED_MIN) | (df["Speed"] > SPEED_MAX)
        abnormal_count = abnormal_speed.sum()

        print(f"  异常速度记录: {abnormal_count:,} 条 ({abnormal_count/before*100:.2f}%)")

        # 将异常值设为NaN，然后按车辆分组线性插值
        df_clean = df.copy()
        df_clean.loc[abnormal_speed, "Speed"] = np.nan

        # 按车辆分组插值
        df_clean["Speed"] = df_clean.groupby("VehicleNum")["Speed"].transform(
            lambda x: x.interpolate(method="linear", limit_direction="both")
        )

        # 剔除仍然为NaN的记录（无法插值的）
        still_nan = df_clean["Speed"].isna().sum()
        if still_nan > 0:
            print(f"  仍有 {still_nan} 条无法插值，予以剔除")
            df_clean = df_clean.dropna(subset=["Speed"])

        removed = before - len(df_clean)
        print(f"  处理后: {len(df_clean):,} 条")

        self._log_step("规则2-异常速度处理", before, len(df_clean), removed)
        return df_clean

    # ----------------------------------------------------------
    # 规则3 & 4: 载客行程切片 + OD提取
    # ----------------------------------------------------------
    def extract_trips(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从GPS点序列中提取载客行程的OD信息

        核心逻辑:
          按车辆分组 → 识别OpenStatus从1→0切换(行程开始)
          → 从0→1切换(行程结束) → 提取起止点信息

        Parameters
        ----------
        df : pd.DataFrame
            经规则2处理后的GPS数据

        Returns
        -------
        pd.DataFrame
            包含 VehicleNum, Stime, SLng, SLat, ELng, ELat, Etime 的出行OD数据
        """
        print(f"\n[规则3&4] 载客行程切片与OD提取...")
        start_time = time.time()

        trips = []
        skipped = 0  # 未闭合行程计数

        # 按车辆分组处理
        for vehicle, group in df.groupby("VehicleNum"):
            # 按时间排序
            group = group.sort_values("Stime")

            # 状态切换检测
            status = group["OpenStatus"].values
            times = group["Stime"].values
            lngs = group["Lng"].values
            lats = group["Lat"].values

            # 寻找状态切换点
            # 1→0: 行程开始（上车）
            # 0→1: 行程结束（下车）
            trip_start_idx = []
            trip_end_idx = []

            for i in range(1, len(status)):
                # 行程开始: 空车→载客
                if status[i-1] == 1 and status[i] == 0:
                    trip_start_idx.append(i)
                # 行程结束: 载客→空车
                elif status[i-1] == 0 and status[i] == 1:
                    trip_end_idx.append(i)

            # 匹配行程起止点
            # 策略: 每个start配对其后第一个end
            end_ptr = 0
            for start_i in trip_start_idx:
                # 找到start之后的第一个end
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

        # 构建DataFrame
        trips_df = pd.DataFrame(trips)

        elapsed = time.time() - start_time
        print(f"  提取行程数: {len(trips_df):,}")
        print(f"  丢弃未闭合行程: {skipped:,}")
        print(f"  耗时: {elapsed:.2f}秒")

        self._log_step("规则3&4-行程切片与OD提取",
                       before=len(df),
                       after=len(trips_df),
                       removed=len(df) - len(trips_df))
        return trips_df

    # ----------------------------------------------------------
    # 规则5: 异常行程过滤
    # ----------------------------------------------------------
    def filter_abnormal_trips(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤不合理行程

        过滤条件:
          - 行程时长 < 1分钟 或 > 4小时
          - 行程距离 < 200米
          - 平均速度不在 5-100 km/h 范围内

        Parameters
        ----------
        df : pd.DataFrame
            行程OD数据

        Returns
        -------
        pd.DataFrame
            过滤后的数据
        """
        before = len(df)
        print(f"\n[规则5] 异常行程过滤...")

        df = df.copy()

        # 计算行程时长（分钟）
        df["stime_dt"] = pd.to_datetime(df["Stime"], format="%H:%M:%S")
        df["etime_dt"] = pd.to_datetime(df["Etime"], format="%H:%M:%S")

        # 处理跨日情况（Etime < Stime）
        mask_cross_day = df["etime_dt"] < df["stime_dt"]
        df.loc[mask_cross_day, "etime_dt"] += pd.Timedelta(days=1)

        df["duration_min"] = (
            (df["etime_dt"] - df["stime_dt"]).dt.total_seconds() / 60
        )

        # 计算行程距离（公里）- 使用Haversine近似
        df["distance_km"] = self._haversine_distance(
            df["SLng"], df["SLat"], df["ELng"], df["ELat"]
        )

        # 计算平均速度
        df["avg_speed"] = np.where(
            df["duration_min"] > 0,
            df["distance_km"] / (df["duration_min"] / 60),
            0
        )

        # 应用过滤条件
        cond_duration_min = df["duration_min"] >= TRIP_DURATION_MIN
        cond_duration_max = df["duration_min"] <= TRIP_DURATION_MAX
        cond_distance = df["distance_km"] >= TRIP_DISTANCE_MIN
        cond_speed_min = df["avg_speed"] >= TRIP_AVG_SPEED_MIN
        cond_speed_max = df["avg_speed"] <= TRIP_AVG_SPEED_MAX

        # 统计各条件过滤数
        print(f"  过滤条件:")
        print(f"    时长<{TRIP_DURATION_MIN}分钟: {(~cond_duration_min).sum():,}")
        print(f"    时长>{TRIP_DURATION_MAX}分钟: {(~cond_duration_max).sum():,}")
        print(f"    距离<{TRIP_DISTANCE_MIN}km: {(~cond_distance).sum():,}")
        print(f"    均速<{TRIP_AVG_SPEED_MIN}km/h: {(~cond_speed_min).sum():,}")
        print(f"    均速>{TRIP_AVG_SPEED_MAX}km/h: {(~cond_speed_max).sum():,}")

        # 综合过滤
        valid = (cond_duration_min & cond_duration_max &
                 cond_distance & cond_speed_min & cond_speed_max)

        df_clean = df[valid].copy()

        # 清理辅助列，只保留需要的字段
        df_clean = df_clean[["VehicleNum", "Stime", "SLng", "SLat",
                              "ELng", "ELat", "Etime"]]

        removed = before - len(df_clean)
        print(f"  过滤前: {before:,} 条")
        print(f"  过滤后: {len(df_clean):,} 条")
        print(f"  剔除: {removed:,} 条 ({removed/before*100:.2f}%)")

        self._log_step("规则5-异常行程过滤", before, len(df_clean), removed)
        return df_clean

    # ----------------------------------------------------------
    # 完整清洗流水线
    # ----------------------------------------------------------
    def run_pipeline(self, df: pd.DataFrame,
                     skip_to_od: bool = False) -> pd.DataFrame:
        """
        执行完整的数据清洗流水线

        Parameters
        ----------
        df : pd.DataFrame
            原始GPS数据 (含 VehicleNum, Stime, Lng, Lat, OpenStatus, Speed)
        skip_to_od : bool
            如果数据已经是OD格式，跳过GPS→OD转换步骤

        Returns
        -------
        pd.DataFrame
            清洗后的出行OD数据
        """
        print("\n" + "=" * 60)
        print("  开始数据清洗流水线")
        print("=" * 60)
        total_start = time.time()

        current = df.copy()

        if not skip_to_od:
            # 步骤1: 异常坐标过滤
            current = self.filter_abnormal_coords(current)

            # 步骤2: 异常速度处理
            current = self.handle_abnormal_speed(current)

            # 步骤3&4: 行程切片与OD提取
            current = self.extract_trips(current)
        else:
            print("\n[INFO] 跳过GPS→OD转换，直接进行行程过滤")

        # 步骤5: 异常行程过滤
        current = self.filter_abnormal_trips(current)

        total_elapsed = time.time() - total_start
        print(f"\n[完成] 清洗流水线总耗时: {total_elapsed:.2f}秒")
        print(f"[完成] 最终输出: {len(current):,} 条有效行程记录")

        return current

    # ----------------------------------------------------------
    # 导出
    # ----------------------------------------------------------
    def export_cleaned_data(self, df: pd.DataFrame, filepath: str) -> None:
        """
        导出清洗后的数据为CSV文件 (UTF-8 with BOM, 兼容Excel)

        Parameters
        ----------
        df : pd.DataFrame
            清洗后的OD数据
        filepath : str
            输出文件路径
        """
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"[INFO] 清洗数据已导出至: {filepath}")

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------
    @staticmethod
    def _haversine_distance(lng1, lat1, lng2, lat2):
        """
        Haversine公式计算两点间距离（公里）

        Parameters
        ----------
        lng1, lat1 : array-like
            起点经纬度
        lng2, lat2 : array-like
            终点经纬度

        Returns
        -------
        array-like
            距离（公里）
        """
        R = 6371.0  # 地球半径 (km)

        # 转换为弧度
        lng1_r = np.radians(lng1)
        lat1_r = np.radians(lat1)
        lng2_r = np.radians(lng2)
        lat2_r = np.radians(lat2)

        # Haversine公式
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
        for log in self.cleaning_log:
            lines.append(
                f"  {log['step']}: {log['before']:,} → {log['after']:,} "
                f"(剔除 {log['removed']:,}, {log['removal_rate']:.2f}%)"
            )
        return "\n".join(lines)
