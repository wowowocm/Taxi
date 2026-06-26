# -*- coding: utf-8 -*-
"""
可视化模块
功能:
  1. 地图热力图 (基于Folium)
  2. 时序折线图 (24小时出行量)
  3. 行程时长/距离分布直方图
  4. 热点区域柱状图
  5. OD流向可视化
  6. 关键指标卡片
  7. 交互式数据看板 (Flask + ECharts)
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 非交互后端
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from .config import (
    FIGURES_DIR, MAP_CENTER, MAP_DEFAULT_ZOOM,
    CHART_STYLE, TIME_PERIODS,
)

# 应用全局样式
plt.rcParams.update(CHART_STYLE)


class Visualizer:
    """可视化器"""

    def __init__(self):
        self.temporal_analyzer = None
        self.spatial_analyzer = None

    def set_analyzers(self, temporal_analyzer, spatial_analyzer):
        """绑定分析模块，获取分析结果用于可视化"""
        self.temporal_analyzer = temporal_analyzer
        self.spatial_analyzer = spatial_analyzer

    # ----------------------------------------------------------
    # 地图热力图 (Folium)
    # ----------------------------------------------------------
    def heatmap_map(self, density_df: pd.DataFrame,
                    title: str = "出行热力分布",
                    filename: str = "heatmap.html") -> str:
        """
        生成交互式热力地图

        Parameters
        ----------
        density_df : pd.DataFrame
            含 lng, lat, count 的密度数据
        title : str
            地图标题
        filename : str
            输出文件名

        Returns
        -------
        str
            输出文件路径
        """
        try:
            import folium
            from folium.plugins import HeatMap
        except ImportError:
            print("[WARN] Folium未安装，跳过地图生成")
            return ""

        # 创建地图
        m = folium.Map(
            location=MAP_CENTER,
            zoom_start=MAP_DEFAULT_ZOOM,
            tiles="OpenStreetMap",
            control_scale=True,
        )

        # 添加热力图层
        heat_data = density_df[["lat", "lng", "count"]].values.tolist()
        HeatMap(
            heat_data,
            radius=12,
            blur=8,
            max_zoom=13,
            min_opacity=0.3,
        ).add_to(m)

        # 添加标题
        folium.Element(f'<h3 style="text-align:center">{title}</h3>').add_to(m)

        # 保存
        filepath = os.path.join(FIGURES_DIR, filename)
        m.save(filepath)
        print(f"[INFO] 热力地图已保存: {filepath}")

        return filepath

    def period_heatmaps(self, period_density: dict) -> list:
        """
        按时段生成多张热力地图

        Parameters
        ----------
        period_density : dict
            {时段名: density_DataFrame}

        Returns
        -------
        list
            输出文件路径列表
        """
        files = []
        for period_name, density in period_density.items():
            if density.empty:
                continue
            fname = f"heatmap_{period_name}.html"
            path = self.heatmap_map(density, title=f"{period_name} - 出行热力", filename=fname)
            files.append(path)
        return files

    # ----------------------------------------------------------
    # 时序折线图
    # ----------------------------------------------------------
    def hourly_trip_chart(self, hourly_df: pd.DataFrame = None,
                          filename: str = "hourly_trips.png") -> str:
        """
        生成24小时出行量折线图

        Parameters
        ----------
        hourly_df : pd.DataFrame
            含 hour, trip_count 的数据
        filename : str
            输出文件名

        Returns
        -------
        str
            保存路径
        """
        if hourly_df is None and self.temporal_analyzer is not None:
            hourly_df = self.temporal_analyzer.hourly_trip_count()

        if hourly_df is None:
            print("[WARN] 无小时统计数据")
            return ""

        fig, ax = plt.subplots(figsize=(14, 6))

        # 折线图
        ax.plot(hourly_df["hour"], hourly_df["trip_count"],
                color="#2196F3", linewidth=2, marker="o",
                markersize=4, label="出行量")

        # 填充区域
        ax.fill_between(hourly_df["hour"], hourly_df["trip_count"],
                         alpha=0.15, color="#2196F3")

        # 标注高峰
        mean_val = hourly_df["trip_count"].mean()
        ax.axhline(y=mean_val, color="gray", linestyle="--",
                   alpha=0.6, label=f"均值 ({mean_val:.0f})")

        ax.axhline(y=mean_val * 1.5, color="red", linestyle="--",
                   alpha=0.4, label=f"高峰阈值 (1.5x均值)")

        # 标注时段背景
        for period_name, (start, end) in TIME_PERIODS.items():
            start_h = int(start.split(":")[0])
            end_h = int(end.split(":")[0])
            if end_h <= start_h:  # 夜间跨日
                end_h += 24
            colors = {"早高峰": "rgba(255,152,0,0.08)",
                      "日间平峰": "rgba(76,175,80,0.05)",
                      "晚高峰": "rgba(255,87,34,0.08)",
                      "夜间": "rgba(63,81,181,0.05)"}
            ax.axvspan(start_h, end_h, color=colors.get(period_name, "none"),
                       alpha=0.5, label=period_name)

        ax.set_xlabel("小时 (Hour)", fontsize=12)
        ax.set_ylabel("出行量 (次)", fontsize=12)
        ax.set_title("24小时出行量时间分布", fontsize=15, fontweight="bold")
        ax.set_xticks(range(0, 24, 2))
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-0.5, 23.5)

        plt.tight_layout()
        filepath = os.path.join(FIGURES_DIR, filename)
        fig.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[INFO] 时序图已保存: {filepath}")

        return filepath

    # ----------------------------------------------------------
    # 行程时长/距离直方图
    # ----------------------------------------------------------
    def duration_histogram(self, duration_stats: dict = None,
                           filename: str = "duration_dist.png") -> str:
        """
        生成行程时长分布直方图 + KDE曲线

        Parameters
        ----------
        duration_stats : dict
            含 segments 统计数据
        filename : str
            输出文件名

        Returns
        -------
        str
            保存路径
        """
        if duration_stats is None and self.temporal_analyzer is not None:
            duration_stats = self.temporal_analyzer.duration_distribution()

        if duration_stats is None:
            print("[WARN] 无时长统计数据")
            return ""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # 子图1: 分段柱状图
        segments = duration_stats.get("segments", {})
        labels = list(segments.keys())
        values = list(segments.values())

        colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(labels)))
        bars = ax1.bar(range(len(labels)), values, color=colors, edgecolor="white")

        # 添加数值标签
        for bar, val in zip(bars, values):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                     f"{val:,}\n({val/sum(values)*100:.1f}%)",
                     ha="center", va="bottom", fontsize=8)

        ax1.set_xticks(range(len(labels)))
        ax1.set_xticklabels(labels, rotation=30, ha="right")
        ax1.set_ylabel("行程数量 (次)", fontsize=12)
        ax1.set_title("行程时长分段分布", fontsize=13, fontweight="bold")
        ax1.grid(True, alpha=0.3, axis="y")

        # 子图2: 统计指标
        ax2.axis("off")
        stats_text = f"""
        行程时长统计指标
        {'='*30}
        均值:   {duration_stats.get('mean', 0):.1f} 分钟
        中位数: {duration_stats.get('median', 0):.1f} 分钟
        标准差: {duration_stats.get('std', 0):.1f} 分钟
        最小值: {duration_stats.get('min', 0):.1f} 分钟
        最大值: {duration_stats.get('max', 0):.1f} 分钟

        分位数:
          P25: {duration_stats.get('percentiles', {}).get('25%', 0):.1f} 分钟
          P50: {duration_stats.get('percentiles', {}).get('50%', 0):.1f} 分钟
          P75: {duration_stats.get('percentiles', {}).get('75%', 0):.1f} 分钟
          P90: {duration_stats.get('percentiles', {}).get('90%', 0):.1f} 分钟
          P95: {duration_stats.get('percentiles', {}).get('95%', 0):.1f} 分钟

        偏度: {duration_stats.get('skewness', 0):.2f}
        峰度: {duration_stats.get('kurtosis', 0):.2f}
        """
        ax2.text(0.1, 0.95, stats_text, transform=ax2.transAxes,
                 fontsize=10, verticalalignment="top",
                 fontfamily="monospace",
                 bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

        plt.tight_layout()
        filepath = os.path.join(FIGURES_DIR, filename)
        fig.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[INFO] 时长分布图已保存: {filepath}")

        return filepath

    # ----------------------------------------------------------
    # 热点区域柱状图
    # ----------------------------------------------------------
    def hotspot_bar_chart(self, hotspots_df: pd.DataFrame = None,
                          filename: str = "hotspots_bar.png") -> str:
        """
        生成Top-N热点区域柱状图

        Parameters
        ----------
        hotspots_df : pd.DataFrame
            含 cluster_id, center_lng, center_lat, count
        filename : str
            输出文件名

        Returns
        -------
        str
        """
        if hotspots_df is None and self.spatial_analyzer is not None:
            hotspots_df = self.spatial_analyzer.hotspots

        if hotspots_df is None or hotspots_df.empty:
            print("[WARN] 无热点数据")
            return ""

        fig, ax = plt.subplots(figsize=(12, 7))

        # 取Top-15用于显示
        top15 = hotspots_df.head(15)

        # 水平柱状图
        labels = [f"#{int(cid)} ({lng:.3f},{lat:.3f})"
                  for cid, lng, lat in zip(top15["cluster_id"],
                                           top15["center_lng"],
                                           top15["center_lat"])]
        colors = plt.cm.OrRd(np.linspace(0.4, 0.95, len(top15)))

        bars = ax.barh(range(len(top15)), top15["count"], color=colors,
                       edgecolor="white", height=0.7)

        # 数值标签
        for i, (bar, val) in enumerate(zip(bars, top15["count"])):
            ax.text(bar.get_width() + max(top15["count"]) * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:,}次", va="center", fontsize=9)

        ax.set_yticks(range(len(top15)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("出行量 (次)", fontsize=12)
        ax.set_title("Top-15 出行热点区域", fontsize=14, fontweight="bold")
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3, axis="x")

        plt.tight_layout()
        filepath = os.path.join(FIGURES_DIR, filename)
        fig.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[INFO] 热点柱状图已保存: {filepath}")

        return filepath

    # ----------------------------------------------------------
    # 出行距离 vs 时长散点图
    # ----------------------------------------------------------
    def scatter_duration_distance(self,
                                  filename: str = "scatter_duration_dist.png") -> str:
        """
        生成行程时长 vs 距离散点图

        Returns
        -------
        str
        """
        if self.temporal_analyzer is None or self.temporal_analyzer.df is None:
            print("[WARN] 无分析数据")
            return ""

        df = self.temporal_analyzer.df

        fig, ax = plt.subplots(figsize=(10, 8))

        # 采样以避免过度绘制
        sample = df.sample(min(50000, len(df)), random_state=42)

        ax.scatter(sample["duration_min"], sample["distance_km"],
                   c="#2196F3", alpha=0.3, s=10, edgecolors="none")

        ax.set_xlabel("行程时长 (分钟)", fontsize=12)
        ax.set_ylabel("行程距离 (公里)", fontsize=12)
        ax.set_title("行程时长 vs 距离", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)

        # 添加统计信息
        corr = sample["duration_min"].corr(sample["distance_km"])
        ax.text(0.95, 0.05, f"相关系数 r = {corr:.3f}",
                transform=ax.transAxes, fontsize=11,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

        plt.tight_layout()
        filepath = os.path.join(FIGURES_DIR, filename)
        fig.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[INFO] 散点图已保存: {filepath}")

        return filepath

    # ----------------------------------------------------------
    # 综合看板
    # ----------------------------------------------------------
    def create_dashboard(self, output_dir: str = None) -> str:
        """
        创建综合可视化看板（静态HTML）

        将所有图表组合为一个HTML页面

        Returns
        -------
        str
            输出HTML文件路径
        """
        output_dir = output_dir or FIGURES_DIR
        os.makedirs(output_dir, exist_ok=True)

        # 生成各子图
        chart_files = []

        # 1. 时序图
        if self.temporal_analyzer:
            f = self.hourly_trip_chart()
            if f:
                chart_files.append(("24小时出行量分布", "hourly_trips.png"))

            f = self.duration_histogram()
            if f:
                chart_files.append(("行程时长分布", "duration_dist.png"))

            f = self.scatter_duration_distance()
            if f:
                chart_files.append(("时长vs距离", "scatter_duration_dist.png"))

        # 2. 热点图
        if self.spatial_analyzer and self.spatial_analyzer.hotspots is not None:
            f = self.hotspot_bar_chart()
            if f:
                chart_files.append(("热点区域排名", "hotspots_bar.png"))

        # 构建HTML
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<title>深圳出租车出行分析看板</title>',
            '<style>',
            '  body { font-family: "Microsoft YaHei", sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }',
            '  h1 { text-align: center; color: #333; }',
            '  .dashboard { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }',
            '  .card { background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 15px; }',
            '  .card h3 { margin: 0 0 10px 0; color: #555; }',
            '  .card img { max-width: 100%; height: auto; }',
            '  .kpi-row { display: flex; gap: 20px; justify-content: center; margin: 20px 0; }',
            '  .kpi-card { background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);',
            '               padding: 20px 30px; text-align: center; min-width: 150px; }',
            '  .kpi-value { font-size: 32px; font-weight: bold; color: #2196F3; }',
            '  .kpi-label { font-size: 14px; color: #888; }',
            '</style>',
            '</head>',
            '<body>',
            '<h1>🚕 深圳出租车出行行为分析看板</h1>',
        ]

        # KPI指标卡片
        if self.temporal_analyzer and self.temporal_analyzer.df is not None:
            ta = self.temporal_analyzer
            if ta.hourly_stats is None:
                ta.hourly_trip_count()
            if ta.peak_info is None:
                ta.identify_peak_hours()

            total_trips = len(ta.df)
            total_vehicles = ta.df["VehicleNum"].nunique()
            avg_duration = ta.df["duration_min"].mean()
            peak_hour = ta.peak_info.get("peak_hour_max", 0)
            peak_trips = ta.peak_info.get("peak_max_trips", 0)

            html_parts.extend([
                '<div class="kpi-row">',
                f'<div class="kpi-card"><div class="kpi-value">{total_trips:,}</div><div class="kpi-label">总出行量 (次)</div></div>',
                f'<div class="kpi-card"><div class="kpi-value">{total_vehicles:,}</div><div class="kpi-label">活跃车辆 (辆)</div></div>',
                f'<div class="kpi-card"><div class="kpi-value">{avg_duration:.1f}</div><div class="kpi-label">平均时长 (分钟)</div></div>',
                f'<div class="kpi-card"><div class="kpi-value">{int(peak_hour)}:00</div><div class="kpi-label">高峰时段</div></div>',
                f'<div class="kpi-card"><div class="kpi-value">{peak_trips:,}</div><div class="kpi-label">高峰出行量 (次)</div></div>',
                '</div>',
            ])

        # 图表区域
        html_parts.append('<div class="dashboard">')
        for title, fname in chart_files:
            html_parts.extend([
                '<div class="card">',
                f'<h3>{title}</h3>',
                f'<img src="{fname}" alt="{title}">',
                '</div>',
            ])
        html_parts.append('</div>')

        html_parts.extend([
            '</body>',
            '</html>',
        ])

        # 写入文件
        html_path = os.path.join(output_dir, "dashboard.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))

        print(f"[INFO] 综合看板已生成: {html_path}")
        return html_path
