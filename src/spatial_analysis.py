# -*- coding: utf-8 -*-
"""
空间分析模块 (支持 Pandas + PySpark 双模式)
功能:
  1. 出行起止点热力分布 (按时段)
  2. 区域 OD 矩阵构建
  3. DBSCAN 空间聚类 → 热点区域识别
  4. 行政区级 OD 流量分析
"""

import pandas as pd
import numpy as np
from .config import (
    SHENZHEN_LNG_MIN, SHENZHEN_LNG_MAX,
    SHENZHEN_LAT_MIN, SHENZHEN_LAT_MAX,
    GRID_SIZE_LNG, GRID_SIZE_LAT,
    DBSCAN_EPS, DBSCAN_MIN_SAMPLES,
    TOP_N_HOTSPOTS, TIME_PERIODS,
)


class SpatialAnalyzer:
    """空间分析器 (Pandas + PySpark 双模式)"""

    def __init__(self, df: pd.DataFrame = None, use_spark: bool = False):
        """
        Parameters
        ----------
        df : pd.DataFrame
            清洗后的 OD 数据
        use_spark : bool
            是否使用 PySpark 进行空间分析
        """
        self.df = df
        self.grid_od_matrix = None
        self.hotspots = None
        self.grid_labels = None
        self.n_lng = None
        self.n_lat = None
        self.use_spark = use_spark
        self.spark = None  # 延迟初始化
        self._sdf = None   # 缓存的 Spark DataFrame (避免重复转换)

    def _get_spark(self):
        """延迟初始化 Spark 会话"""
        if self.spark is None and self.use_spark:
            from .spark_manager import get_spark
            self.spark = get_spark()
            if self.spark is None:
                self.use_spark = False
        return self.spark

    def _get_sdf(self):
        """获取 Spark DataFrame 版本的数据 (缓存)"""
        if self._sdf is None and self.use_spark and self._get_spark() is not None:
            self._sdf = self.spark.createDataFrame(self.df)
        return self._sdf

    def load_data(self, df: pd.DataFrame):
        """加载 OD 数据"""
        self.df = df.copy()
        self._sdf = None  # 清除缓存
        self.grid_od_matrix = None
        self.hotspots = None

    # ----------------------------------------------------------
    # 网格划分
    # ----------------------------------------------------------

    def _build_grid(self):
        """构建空间网格系统"""
        self.n_lng = int((SHENZHEN_LNG_MAX - SHENZHEN_LNG_MIN) / GRID_SIZE_LNG) + 1
        self.n_lat = int((SHENZHEN_LAT_MAX - SHENZHEN_LAT_MIN) / GRID_SIZE_LAT) + 1
        print(f"[INFO] 网格划分: {self.n_lng} × {self.n_lat} "
              f"= {self.n_lng * self.n_lat} 个网格")

    def _get_grid_cell(self, lng, lat):
        """根据经纬度获取网格索引"""
        i_lng = ((lng - SHENZHEN_LNG_MIN) / GRID_SIZE_LNG).astype(int)
        i_lat = ((lat - SHENZHEN_LAT_MIN) / GRID_SIZE_LAT).astype(int)
        i_lng = np.clip(i_lng, 0, self.n_lng - 1)
        i_lat = np.clip(i_lat, 0, self.n_lat - 1)
        return i_lng, i_lat

    def _grid_to_center(self, i_lng, i_lat):
        """网格索引转中心经纬度"""
        lng = SHENZHEN_LNG_MIN + (i_lng + 0.5) * GRID_SIZE_LNG
        lat = SHENZHEN_LAT_MIN + (i_lat + 0.5) * GRID_SIZE_LAT
        return lng, lat

    # ----------------------------------------------------------
    # 出行热力分布
    # ----------------------------------------------------------

    def trip_density(self, point_type: str = "start") -> pd.DataFrame:
        """
        计算出行起止点的空间密度分布

        Parameters
        ----------
        point_type : str
            "start" (起点), "end" (终点), "both" (两者合计)

        Returns
        -------
        pd.DataFrame
            含 lng, lat, density(即count) 的密度数据
        """
        if self.df is None:
            raise ValueError("请先加载数据")
        if self.n_lng is None:
            self._build_grid()

        # PySpark 模式
        sdf = self._get_sdf()
        if sdf is not None:
            return self._spark_trip_density(point_type)

        # Pandas 模式
        if point_type == "both":
            combined = pd.concat([
                self.df[["SLng", "SLat"]].rename(columns={"SLng": "lng", "SLat": "lat"}),
                self.df[["ELng", "ELat"]].rename(columns={"ELng": "lng", "ELat": "lat"}),
            ])
            i_lng, i_lat = self._get_grid_cell(combined["lng"], combined["lat"])
            density = pd.DataFrame({"i_lng": i_lng, "i_lat": i_lat})
            density = density.groupby(["i_lng", "i_lat"]).size().reset_index(name="count")
            density["lng"], density["lat"] = self._grid_to_center(
                density["i_lng"], density["i_lat"]
            )
            return density

        lng_col = "SLng" if point_type == "start" else "ELng"
        lat_col = "SLat" if point_type == "start" else "ELat"

        i_lng, i_lat = self._get_grid_cell(self.df[lng_col], self.df[lat_col])
        density = pd.DataFrame({"i_lng": i_lng, "i_lat": i_lat})
        density = density.groupby(["i_lng", "i_lat"]).size().reset_index(name="count")
        density["lng"], density["lat"] = self._grid_to_center(
            density["i_lng"], density["i_lat"]
        )
        return density

    def _spark_trip_density(self, point_type: str) -> pd.DataFrame:
        """PySpark 版本: 出行热力分布"""
        from pyspark.sql import functions as F

        sdf = self._get_sdf()

        if point_type == "both":
            sdf_start = sdf.select(
                F.col("SLng").alias("lng"),
                F.col("SLat").alias("lat"),
            )
            sdf_end = sdf.select(
                F.col("ELng").alias("lng"),
                F.col("ELat").alias("lat"),
            )
            sdf_combined = sdf_start.union(sdf_end)
        elif point_type == "start":
            sdf_combined = sdf.select(
                F.col("SLng").alias("lng"),
                F.col("SLat").alias("lat"),
            )
        else:
            sdf_combined = sdf.select(
                F.col("ELng").alias("lng"),
                F.col("ELat").alias("lat"),
            )

        # 计算网格索引
        grid_expr_lng = F.least(
            F.lit(self.n_lng - 1),
            F.greatest(F.lit(0),
                ((F.col("lng") - SHENZHEN_LNG_MIN) / GRID_SIZE_LNG).cast("int")
            )
        )
        grid_expr_lat = F.least(
            F.lit(self.n_lat - 1),
            F.greatest(F.lit(0),
                ((F.col("lat") - SHENZHEN_LAT_MIN) / GRID_SIZE_LAT).cast("int")
            )
        )

        density = sdf_combined \
            .withColumn("i_lng", grid_expr_lng) \
            .withColumn("i_lat", grid_expr_lat) \
            .groupBy("i_lng", "i_lat") \
            .agg(F.count("*").alias("count")) \
            .toPandas()

        if len(density) == 0:
            return pd.DataFrame(columns=["i_lng", "i_lat", "count", "lng", "lat"])

        density["lng"], density["lat"] = self._grid_to_center(
            density["i_lng"].values, density["i_lat"].values
        )
        return density

    def period_density(self) -> dict:
        """按时段分别计算起点密度分布"""
        results = {}
        for period_name, (start, end) in TIME_PERIODS.items():
            mask = (self.df["Stime"] >= start) & (self.df["Stime"] < end)
            period_df = self.df[mask]

            if len(period_df) == 0:
                results[period_name] = pd.DataFrame()
                continue

            original = self.df
            self.df = period_df
            self._sdf = None  # 清除缓存 (数据变了)
            results[period_name] = self.trip_density("start")
            self.df = original
            self._sdf = None  # 恢复后清除缓存

        return results

    # ----------------------------------------------------------
    # OD 矩阵构建
    # ----------------------------------------------------------

    def build_od_matrix(self) -> np.ndarray:
        """
        构建区域间 OD 矩阵

        Returns
        -------
        np.ndarray
            n_grids × n_grids 的 OD 矩阵
        """
        if self.df is None:
            raise ValueError("请先加载数据")
        if self.n_lng is None:
            self._build_grid()

        print(f"[INFO] 构建OD矩阵... (网格: {self.n_lng}×{self.n_lat})")

        # PySpark 模式
        sdf = self._get_sdf()
        if sdf is not None:
            return self._spark_build_od_matrix()

        # Pandas 模式
        o_lng, o_lat = self._get_grid_cell(self.df["SLng"], self.df["SLat"])
        d_lng, d_lat = self._get_grid_cell(self.df["ELng"], self.df["ELat"])

        o_id = o_lng * self.n_lat + o_lat
        d_id = d_lng * self.n_lat + d_lat

        n_grids = self.n_lng * self.n_lat
        od_flat = pd.DataFrame({"o": o_id, "d": d_id})
        od_flat = od_flat.groupby(["o", "d"]).size().reset_index(name="flow")

        od_matrix = np.zeros((n_grids, n_grids), dtype=int)
        for _, row in od_flat.iterrows():
            od_matrix[int(row["o"]), int(row["d"])] = int(row["flow"])

        self.grid_od_matrix = od_matrix

        total_flow = od_matrix.sum()
        internal_flow = np.trace(od_matrix)
        print(f"  OD矩阵大小: {n_grids}×{n_grids}")
        print(f"  总出行量: {total_flow:,}")
        print(f"  内部出行(对角): {internal_flow:,} ({internal_flow/total_flow*100:.1f}%)")

        return od_matrix

    def _spark_build_od_matrix(self) -> np.ndarray:
        """PySpark 版本: 构建 OD 矩阵"""
        from pyspark.sql import functions as F

        sdf = self._get_sdf()
        n_grids = self.n_lng * self.n_lat

        # 计算 O/D 网格索引
        grid_lng = F.least(
            F.lit(self.n_lng - 1),
            F.greatest(F.lit(0),
                ((F.col("SLng") - SHENZHEN_LNG_MIN) / GRID_SIZE_LNG).cast("int")
            )
        )
        grid_lat = F.least(
            F.lit(self.n_lat - 1),
            F.greatest(F.lit(0),
                ((F.col("SLat") - SHENZHEN_LAT_MIN) / GRID_SIZE_LAT).cast("int")
            )
        )
        o_id = grid_lng * self.n_lat + grid_lat

        grid_lng_d = F.least(
            F.lit(self.n_lng - 1),
            F.greatest(F.lit(0),
                ((F.col("ELng") - SHENZHEN_LNG_MIN) / GRID_SIZE_LNG).cast("int")
            )
        )
        grid_lat_d = F.least(
            F.lit(self.n_lat - 1),
            F.greatest(F.lit(0),
                ((F.col("ELat") - SHENZHEN_LAT_MIN) / GRID_SIZE_LAT).cast("int")
            )
        )
        d_id = grid_lng_d * self.n_lat + grid_lat_d

        # 按 (o, d) 分组统计
        od_counts = sdf \
            .withColumn("o", o_id) \
            .withColumn("d", d_id) \
            .groupBy("o", "d") \
            .agg(F.count("*").alias("flow")) \
            .toPandas()

        # 构建 numpy 矩阵
        od_matrix = np.zeros((n_grids, n_grids), dtype=int)
        for _, row in od_counts.iterrows():
            o, d, f = int(row["o"]), int(row["d"]), int(row["flow"])
            od_matrix[o, d] = f

        self.grid_od_matrix = od_matrix

        total_flow = od_matrix.sum()
        internal_flow = np.trace(od_matrix)
        print(f"  OD矩阵大小: {n_grids}×{n_grids}")
        print(f"  总出行量: {total_flow:,}")
        print(f"  内部出行(对角): {internal_flow:,} ({internal_flow/total_flow*100:.1f}%)")

        return od_matrix

    def top_od_pairs(self, top_n: int = 20) -> pd.DataFrame:
        """获取流量最大的 OD 对"""
        if self.grid_od_matrix is None:
            self.build_od_matrix()

        n = self.grid_od_matrix.shape[0]
        flows = []
        for i in range(n):
            for j in range(n):
                if i != j and self.grid_od_matrix[i, j] > 0:
                    flows.append({
                        "o_grid": i,
                        "d_grid": j,
                        "flow": int(self.grid_od_matrix[i, j]),
                    })

        flows_df = pd.DataFrame(flows)
        flows_df = flows_df.sort_values("flow", ascending=False).head(top_n)

        o_lngs, o_lats = self._grid_to_center(
            flows_df["o_grid"] // self.n_lat,
            flows_df["o_grid"] % self.n_lat,
        )
        d_lngs, d_lats = self._grid_to_center(
            flows_df["d_grid"] // self.n_lat,
            flows_df["d_grid"] % self.n_lat,
        )

        flows_df["O_lng"] = o_lngs
        flows_df["O_lat"] = o_lats
        flows_df["D_lng"] = d_lngs
        flows_df["D_lat"] = d_lats

        print(f"\n--- Top-{top_n} OD对 ---")
        for _, row in flows_df.head(10).iterrows():
            print(f"  ({row['O_lng']:.3f},{row['O_lat']:.3f}) → "
                  f"({row['D_lng']:.3f},{row['D_lat']:.3f}): "
                  f"{row['flow']:,}次")

        return flows_df

    # ----------------------------------------------------------
    # DBSCAN 热点聚类 (始终使用 sklearn, PySpark MLlib 聚类不同)
    # ----------------------------------------------------------

    def find_hotspots(self, point_type: str = "start",
                      eps: float = None,
                      min_samples: int = None) -> pd.DataFrame:
        """使用 DBSCAN 聚类识别出行热点区域"""
        from sklearn.cluster import DBSCAN

        if self.df is None:
            raise ValueError("请先加载数据")

        eps = eps or DBSCAN_EPS
        min_samples = min_samples or DBSCAN_MIN_SAMPLES

        print(f"\n[INFO] DBSCAN聚类: eps={eps}, min_samples={min_samples}")

        if point_type == "start":
            coords = self.df[["SLng", "SLat"]].values
        else:
            coords = self.df[["ELng", "ELat"]].values

        sample_size = min(200000, len(coords))
        if len(coords) > sample_size:
            indices = np.random.choice(len(coords), sample_size, replace=False)
            coords = coords[indices]
            print(f"[INFO] 采样 {sample_size:,} 个点进行聚类")

        lng_scale = 103000
        lat_scale = 111000

        coords_scaled = coords.copy()
        coords_scaled[:, 0] *= lng_scale
        coords_scaled[:, 1] *= lat_scale

        db = DBSCAN(eps=eps * lng_scale, min_samples=min_samples, metric="euclidean")
        labels = db.fit_predict(coords_scaled)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = (labels == -1).sum()
        print(f"  聚类数: {n_clusters}")
        print(f"  噪声点: {n_noise:,} ({n_noise/len(coords)*100:.1f}%)")

        hotspots = []
        for cluster_id in range(n_clusters):
            mask = labels == cluster_id
            cluster_coords = coords[mask]
            hotspots.append({
                "cluster_id": cluster_id,
                "center_lng": cluster_coords[:, 0].mean(),
                "center_lat": cluster_coords[:, 1].mean(),
                "count": mask.sum(),
                "radius_m": np.max(
                    np.sqrt(((cluster_coords - cluster_coords.mean(axis=0)) ** 2).sum(axis=1))
                ) * lng_scale,
            })

        hotspots_df = pd.DataFrame(hotspots)
        hotspots_df = hotspots_df.sort_values("count", ascending=False)
        self.hotspots = hotspots_df.head(TOP_N_HOTSPOTS)

        print(f"\n--- Top-{TOP_N_HOTSPOTS} 出行热点 ---")
        for _, row in self.hotspots.head(10).iterrows():
            print(f"  #{row['cluster_id']}: ({row['center_lng']:.4f},"
                  f"{row['center_lat']:.4f}) - {row['count']:,}次")

        return self.hotspots

    # ----------------------------------------------------------
    # 净流入/流出分析
    # ----------------------------------------------------------

    def net_flow_analysis(self) -> pd.DataFrame:
        """分析各网格区域的净流入/流出"""
        if self.grid_od_matrix is None:
            self.build_od_matrix()

        n = self.grid_od_matrix.shape[0]
        outflow = self.grid_od_matrix.sum(axis=1)
        inflow = self.grid_od_matrix.sum(axis=0)
        net_flow = inflow - outflow

        lngs, lats = [], []
        for i in range(n):
            lng, lat = self._grid_to_center(i // self.n_lat, i % self.n_lat)
            lngs.append(lng)
            lats.append(lat)

        flow_df = pd.DataFrame({
            "grid_id": range(n),
            "lng": lngs,
            "lat": lats,
            "outflow": outflow.astype(int),
            "inflow": inflow.astype(int),
            "net_flow": net_flow.astype(int),
        })

        top_outflow = flow_df.nlargest(10, "outflow")
        top_inflow = flow_df.nlargest(10, "inflow")

        print("\n--- 净流入/流出分析 ---")
        print("主要出发区域 (Top-5):")
        for _, row in top_outflow.head(5).iterrows():
            print(f"  ({row['lng']:.3f},{row['lat']:.3f}): "
                  f"出发{row['outflow']:,}")

        print("主要到达区域 (Top-5):")
        for _, row in top_inflow.head(5).iterrows():
            print(f"  ({row['lng']:.3f},{row['lat']:.3f}): "
                  f"到达{row['inflow']:,}")

        return flow_df

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    def get_summary(self) -> dict:
        """获取空间分析摘要"""
        return {
            "n_grids": self.n_lng * self.n_lat if self.n_lng else 0,
            "grid_size": f"{GRID_SIZE_LNG}°×{GRID_SIZE_LAT}°",
            "hotspot_count": len(self.hotspots) if self.hotspots is not None else 0,
        }
