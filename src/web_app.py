# -*- coding: utf-8 -*-
"""
Flask Web应用
提供交互式数据看板 (前后端分离架构)
后端API + 前端ECharts图表

部署到CentOS VM时运行此文件
"""

import os
import sys

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template_string
from src.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from src.data_loader import DataLoader
from src.temporal_analysis import TemporalAnalyzer
from src.spatial_analysis import SpatialAnalyzer

app = Flask(__name__)

# 全局分析器实例（启动时初始化）
loader = DataLoader()
temporal_analyzer = None
spatial_analyzer = None

# ----------------------------------------------------------
# HTML模板
# ----------------------------------------------------------
DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>城市出行数据分析看板</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: "Microsoft YaHei", sans-serif; background: #f0f2f5; }
        .header { background: linear-gradient(135deg, #1a237e, #283593);
                  color: white; padding: 20px 30px; text-align: center; }
        .header h1 { font-size: 28px; }
        .header p { opacity: 0.8; margin-top: 5px; }
        .kpi-row { display: flex; gap: 15px; padding: 20px; flex-wrap: wrap;
                   justify-content: center; }
        .kpi-card { background: white; border-radius: 10px; padding: 20px 25px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;
                    min-width: 160px; flex: 1; max-width: 220px; }
        .kpi-value { font-size: 30px; font-weight: bold; color: #1a237e; }
        .kpi-label { font-size: 13px; color: #888; margin-top: 5px; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                       gap: 20px; padding: 0 20px 20px; }
        .chart-card { background: white; border-radius: 10px; padding: 15px;
                      box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .chart-card h3 { color: #333; margin-bottom: 10px; font-size: 16px; }
        .chart { width: 100%; height: 380px; }
        .chart-full { grid-column: 1 / -1; }
        .chart-full .chart { height: 450px; }
        .footer { text-align: center; padding: 20px; color: #aaa; font-size: 12px; }
        .loading { text-align: center; padding: 50px; color: #888; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚕 深圳市出租车出行行为分析系统</h1>
        <p>基于GPS轨迹数据的城市出行规律挖掘 | 500辆出租车 × 全天候轨迹</p>
    </div>

    <div class="kpi-row" id="kpi-cards">
        <div class="loading">正在加载KPI数据...</div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <h3>24小时出行量分布</h3>
            <div class="chart" id="chart-hourly"></div>
        </div>
        <div class="chart-card">
            <h3>行程时长分布</h3>
            <div class="chart" id="chart-duration"></div>
        </div>
        <div class="chart-card">
            <h3>各时段出行量对比</h3>
            <div class="chart" id="chart-period"></div>
        </div>
        <div class="chart-card">
            <h3>Top-15 热点区域</h3>
            <div class="chart" id="chart-hotspots"></div>
        </div>
    </div>

    <div class="footer">
        © 2026 城市出行数据分析项目组 | Python + Flask + ECharts
    </div>

    <script>
        // 工具函数：加载数据并渲染
        async function loadData() {
            try {
                const resp = await fetch('/api/dashboard');
                const data = await resp.json();
                renderKPIs(data.kpis);
                renderHourlyChart(data.hourly);
                renderDurationChart(data.duration);
                renderPeriodChart(data.period);
                renderHotspotChart(data.hotspots);
            } catch (e) {
                console.error('数据加载失败:', e);
            }
        }

        // KPI卡片
        function renderKPIs(kpis) {
            const container = document.getElementById('kpi-cards');
            container.innerHTML = kpis.map(k =>
                `<div class="kpi-card">
                    <div class="kpi-value">${k.value}</div>
                    <div class="kpi-label">${k.label}</div>
                </div>`
            ).join('');
        }

        // 24小时出行量折线图
        function renderHourlyChart(data) {
            const chart = echarts.init(document.getElementById('chart-hourly'));
            chart.setOption({
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: data.hours, name: '小时' },
                yAxis: { type: 'value', name: '出行量 (次)' },
                series: [{
                    data: data.values, type: 'line', smooth: true,
                    areaStyle: { color: 'rgba(33,150,243,0.15)' },
                    lineStyle: { color: '#2196F3', width: 2 },
                    itemStyle: { color: '#2196F3' },
                    markLine: {
                        data: [{ type: 'average', name: '均值' }],
                        lineStyle: { color: '#FF5722', type: 'dashed' }
                    }
                }]
            });
        }

        // 行程时长分布柱状图
        function renderDurationChart(data) {
            const chart = echarts.init(document.getElementById('chart-duration'));
            chart.setOption({
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: data.labels, axisLabel: { rotate: 30 } },
                yAxis: { type: 'value', name: '行程数 (次)' },
                series: [{
                    data: data.values, type: 'bar',
                    itemStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[
                        {offset:0, color:'#42A5F5'}, {offset:1, color:'#1E88E5'}
                    ])},
                    label: { show: true, position: 'top', rotate: 45, fontSize: 10 }
                }]
            });
        }

        // 时段对比柱状图
        function renderPeriodChart(data) {
            const chart = echarts.init(document.getElementById('chart-period'));
            chart.setOption({
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: data.labels },
                yAxis: { type: 'value', name: '出行量 (次)' },
                series: [{
                    data: data.values, type: 'bar',
                    itemStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[
                        {offset:0, color:'#FF7043'}, {offset:1, color:'#E64A19'}
                    ])},
                    label: { show: true, position: 'top', formatter: '{c}%',
                             fontSize: 12, fontWeight: 'bold' }
                }]
            });
        }

        // 热点区域柱状图
        function renderHotspotChart(data) {
            const chart = echarts.init(document.getElementById('chart-hotspots'));
            chart.setOption({
                tooltip: { trigger: 'axis' },
                grid: { left: '25%' },
                xAxis: { type: 'value', name: '出行量 (次)' },
                yAxis: { type: 'category', data: data.labels, inverse: true,
                         axisLabel: { fontSize: 10 } },
                series: [{
                    data: data.values, type: 'bar',
                    itemStyle: { color: new echarts.graphic.LinearGradient(0,0,1,0,[
                        {offset:0, color:'#FFA726'}, {offset:1, color:'#FF5722'}
                    ])},
                    label: { show: true, position: 'right', fontSize: 10 }
                }]
            });
        }

        // 页面加载时初始化
        window.addEventListener('DOMContentLoaded', loadData);
    </script>
</body>
</html>
"""


# ----------------------------------------------------------
# 初始化数据
# ----------------------------------------------------------
def init_data():
    """初始化分析器并加载数据"""
    global temporal_analyzer, spatial_analyzer

    print("[INFO] 加载OD数据...")
    df = loader.load_cleaned_data()

    print("[INFO] 初始化时序分析...")
    temporal_analyzer = TemporalAnalyzer(df)

    print("[INFO] 初始化空间分析...")
    spatial_analyzer = SpatialAnalyzer(df)
    spatial_analyzer._build_grid()

    print("[INFO] 初始化完成!")


# ----------------------------------------------------------
# API路由
# ----------------------------------------------------------
@app.route("/")
def index():
    """主页面"""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/dashboard")
def api_dashboard():
    """看板数据API"""
    global temporal_analyzer, spatial_analyzer

    if temporal_analyzer is None:
        init_data()

    # KPI数据
    ta = temporal_analyzer
    if ta.hourly_stats is None:
        ta.hourly_trip_count()
    if ta.peak_info is None:
        ta.identify_peak_hours()

    total_trips = len(ta.df)
    total_vehicles = ta.df["VehicleNum"].nunique()
    avg_duration = ta.df["duration_min"].mean()
    peak_hour = ta.peak_info.get("peak_hour_max", 0)

    kpis = [
        {"label": "总出行量", "value": f"{total_trips:,}"},
        {"label": "活跃车辆", "value": f"{total_vehicles:,}"},
        {"label": "平均时长(分钟)", "value": f"{avg_duration:.1f}"},
        {"label": "高峰时段", "value": f"{int(peak_hour)}:00"},
        {"label": "高峰出行量", "value": f"{ta.peak_info.get('peak_max_trips', 0):,}"},
    ]

    # 小时数据
    hourly = ta.hourly_stats
    hourly_data = {
        "hours": [f"{h:02d}:00" for h in hourly["hour"]],
        "values": hourly["trip_count"].tolist(),
    }

    # 时长分布
    dur_stats = ta.duration_distribution()
    dur_segments = dur_stats.get("segments", {})
    duration_data = {
        "labels": list(dur_segments.keys()),
        "values": list(dur_segments.values()),
    }

    # 时段数据
    period_stats = ta.period_analysis()
    period_data = {
        "labels": period_stats["时段"].tolist(),
        "values": period_stats["占比(%)"].round(1).tolist(),
    }

    # 热点数据
    if spatial_analyzer.hotspots is None:
        spatial_analyzer.find_hotspots("start")
    hotspots = spatial_analyzer.hotspots.head(15)
    hotspot_data = {
        "labels": [f"#{int(r['cluster_id'])} ({r['center_lng']:.3f},{r['center_lat']:.3f})"
                   for _, r in hotspots.iterrows()],
        "values": hotspots["count"].tolist(),
    }

    return jsonify({
        "kpis": kpis,
        "hourly": hourly_data,
        "duration": duration_data,
        "period": period_data,
        "hotspots": hotspot_data,
    })


@app.route("/api/health")
def health():
    """健康检查"""
    return jsonify({"status": "ok", "message": "服务运行正常"})


# ----------------------------------------------------------
# 启动
# ----------------------------------------------------------
if __name__ == "__main__":
    print("=" * 55)
    print("  城市出行数据分析系统 - Flask Web服务")
    print("=" * 55)

    # 预加载数据
    init_data()

    print(f"\n[INFO] 服务地址: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"[INFO] 管理面板: http://localhost:{FLASK_PORT}")
    print()

    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
    )
