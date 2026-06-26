# -*- coding: utf-8 -*-
"""
空间分析模块
功能:
  1. 出行起止点热力分布 (按时段)
  2. 区域OD矩阵构建
  3. DBSCAN空间聚类 → 热点区域识别
  4. 行政区级OD流量分析
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
    """空间分析器"""

    def __init__(self, df: pd.DataFrame = None):
        """
        Parameters
        ----------
        df : pd.DataFrame
            清洗后的OD数据
        """
        self.df = df
        self.grid_od_matrix = None    # 网格OD矩阵
        self.hotspots = None          # 热点区域
        self.grid_labels = None       # 网格标号映射

    def load_data(self, df: pd.DataFrame):
        """加载OD数据"""
        self.df = df.copy()

    # ----------------------------------------------------------
    # 网格划分
    # ----------------------------------------------------------
    def _build_grid(self):
        """构建空间网格系统"""
        # 计算网格数量
        self.n_lng = int((SHENZHEN_LNG_MAX - SHENZHEN_LNG_MIN) / GRID_SIZE_LNG) + 1
        self.n_lat = int((SHENZHEN_LAT_MAX - SHENZHEN_LAT_MIN) / GRID_SIZE_LAT) + 1

        print(f"[INFO] 网格划分: {self.n_lng} × {self.n_lat} "
              f"= {self.n_lng * self.n_lat} 个网格")

    def _get_grid_cell(self, lng, lat):
        """根据经纬度获取网格索引"""
        i_lng = ((lng - SHENZHEN_LNG_MIN) / GRID_SIZE_LNG).astype(int)
        i_lat = ((lat - SHENZHEN_LAT_MIN) / GRID_SIZE_LAT).astype(int)

        # 限制在有效范围内
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
            含 lng, lat, density 的密度数据
        """
        if self.df is None:
            raise ValueError("请先加载数据")

        if self.n_lng is None:
            self._build_grid()

        # 根据类型选择坐标
        if point_type == "start":
            lng_col, lat_col = "SLng", "SLat"
        elif point_type == "end":
            lng_col, lat_col = "ELng", "ELat"
        else:  # both
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

        i_lng, i_lat = self._get_grid_cell(self.df[lng_col], self.df[lat_col])
        density = pd.DataFrame({"i_lng": i_lng, "i_lat": i_lat})
        density = density.groupby(["i_lng", "i_lat"]).size().reset_index(name="count")
        density["lng"], density["lat"] = self._grid_to_center(
            density["i_lng"], density["i_lat"]
        )

        return density

    def period_density(self) -> dict:
        """
        按时段分别计算起点密度分布

        Returns
        -------
        dict
            {时段名: density_DataFrame}
        """
        results = {}
        for period_name, (start, end) in TIME_PERIODS.items():
            mask = (self.df["Stime"] >= start) & (self.df["Stime"] < end)
            period_df = self.df[mask]

            if len(period_df) == 0:
                results[period_name] = pd.DataFrame()
                continue

            # 临时切换数据
            original = self.df
            self.df = period_df
            results[period_name] = self.trip_density("start")
            self.df = original

        return results

    # ----------------------------------------------------------
    # OD矩阵构建
    # ----------------------------------------------------------
    def build_od_matrix(self) -> np.ndarray:
        """
        构建区域间OD矩阵

        Returns
        -------
        np.ndarray
            n_grids × n_grids 的OD矩阵
        """
        if self.df is None:
            raise ValueError("请先加载数据")

        if self.n_lng is None:
            self._build_grid()

        print(f"[INFO] 构建OD矩阵... (网格: {self.n_lng}×{self.n_lat})")

        # 获取O和D的网格索引
        o_lng, o_lat = self._get_grid_cell(self.df["SLng"], self.df["SLat"])
        d_lng, d_lat = self._get_grid_cell(self.df["ELng"], self.df["ELat"])

        # 转换为一维网格ID
        o_id = o_lng * self.n_lat + o_lat
        d_id = d_lng * self.n_lat + d_lat

        # 构建OD矩阵
        n_grids = self.n_lng * self.n_lat
        od_flat = pd.DataFrame({"o": o_id, "d": d_id})
        od_flat = od_flat.groupby(["o", "d"]).size().reset_index(name="flow")

        od_matrix = np.zeros((n_grids, n_grids), dtype=int)
        for _, row in od_flat.iterrows():
            od_matrix[int(row["o"]), int(row["d"])] = int(row["flow"])

        self.grid_od_matrix = od_matrix

        # 统计
        total_flow = od_matrix.sum()
        internal_flow = np.trace(od_matrix)
        print(f"  OD矩阵大小: {n_grids}×{n_grids}")
        print(f"  总出行量: {total_flow:,}")
        print(f"  内部出行(对角): {internal_flow:,} ({internal_flow/total_flow*100:.1f}%)")

        return od_matrix

    def top_od_pairs(self, top_n: int = 20) -> pd.DataFrame:
        """
        获取流量最大的OD对

        Parameters
        ----------
        top_n : int
            返回前N对

        Returns
        -------
        pd.DataFrame
            含 O_lng, O_lat, D_lng, D_lat, flow 的DataFrame
        """
        if self.grid_od_matrix is None:
            self.build_od_matrix()

        # 找出流量最大的OD对
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

        # 转换网格索引为经纬度
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
    # DBSCAN热点聚类
    # ----------------------------------------------------------
    def find_hotspots(self, point_type: str = "start",
                      eps: float = None,
                      min_samples: int = None) -> pd.DataFrame:
        """
        使用DBSCAN聚类识别出行热点区域

        Parameters
        ----------
        point_type : str
            "start" 或 "end"
        eps : float, optional
            聚类半径（度），默认使用配置值
        min_samples : int, optional
            最小样本数，默认使用配置值

        Returns
        -------
        pd.DataFrame
            含 cluster_id, lng, lat, count 的热点数据
        """
        from sklearn.cluster import DBSCAN

        if self.df is None:
            raise ValueError("请先加载数据")

        eps = eps or DBSCAN_EPS
        min_samples = min_samples or DBSCAN_MIN_SAMPLES

        print(f"\n[INFO] DBSCAN聚类: eps={eps}, min_samples={min_samples}")

        # 选择坐标
        if point_type == "start":
            coords = self.df[["SLng", "SLat"]].values
        else:
            coords = self.df[["ELng", "ELat"]].values

        # 可选：采样以提高性能
        sample_size = min(200000, len(coords))
        if len(coords) > sample_size:
            indices = np.random.choice(len(coords), sample_size, replace=False)
            coords = coords[indices]
            print(f"[INFO] 采样 {sample_size:,} 个点进行聚类")

        # DBSCAN聚类（需要转换经纬度到近似米单位）
        # 在深圳纬度(22.5°)，1°经度≈103km, 1°纬度≈111km
        lng_scale = 103000  # 米/度
        lat_scale = 111000  # 米/度

        coords_scaled = coords.copy()
        coords_scaled[:, 0] *= lng_scale
        coords_scaled[:, 1] *= lat_scale

        db = DBSCAN(eps=eps * lng_scale, min_samples=min_samples, metric="euclidean")
        labels = db.fit_predict(coords_scaled)

        # 统计聚类结果
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = (labels == -1).sum()
        print(f"  聚类数: {n_clusters}")
        print(f"  噪声点: {n_noise:,} ({n_noise/len(coords)*100:.1f}%)")

        # 提取每个聚类的统计信息
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

        # 取Top-N
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
        """
        分析各网格区域的净流入/流出

        Returns
        -------
        pd.DataFrame
            含 inflow, outflow, net_flow 的网格流量数据
        """
        if self.grid_od_matrix is None:
            self.build_od_matrix()

        n = self.grid_od_matrix.shape[0]
        outflow = self.grid_od_matrix.sum(axis=1)   # 从该区域出发
        inflow = self.grid_od_matrix.sum(axis=0)     # 到达该区域
        net_flow = inflow - outflow

        # 构建结果DataFrame
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

        # 识别主要流入/流出区域
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
