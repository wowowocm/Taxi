# -*- coding: utf-8 -*-
"""
Flask Web应用 — 交互式数据看板
架构: Jinja2模板 + 静态文件 + 10个细粒度API + 1个聚合API

部署到CentOS VM时运行: python main.py --web
"""

import os
import sys
import numpy as np
import pandas as pd

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template
from src.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from src.data_loader import DataLoader
from src.temporal_analysis import TemporalAnalyzer
from src.spatial_analysis import SpatialAnalyzer
from src.logger import get_logger

# Flask app — 静态文件和模板目录指向 src/ 下
app = Flask(__name__,
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')

log = get_logger()

# 全局分析器实例（启动时初始化）
loader = DataLoader()
temporal_analyzer = None
spatial_analyzer = None


# ================================================================
# 初始化数据
# ================================================================
def init_data(use_spark=False):
    """预加载数据并预计算所有分析结果，确保API秒级响应

    Parameters
    ----------
    use_spark : bool
        是否使用 PySpark 进行分析计算 (连接VM Spark集群)
    """
    global temporal_analyzer, spatial_analyzer

    log.info("正在初始化 Web 看板数据...")
    if use_spark:
        log.info("PySpark 模式已启用")

    # 加载清洗后的OD数据
    df = loader.load_cleaned_data()
    log.info(f"OD数据加载完成: {len(df):,} 条行程, {len(df.columns)} 个字段")

    # 初始化时序分析
    log.info("初始化时序分析器...")
    temporal_analyzer = TemporalAnalyzer(df, use_spark=use_spark)
    temporal_analyzer.hourly_trip_count()
    temporal_analyzer.identify_peak_hours()
    log.info("时序分析器就绪")

    # 初始化空间分析
    log.info("初始化空间分析器...")
    spatial_analyzer = SpatialAnalyzer(df, use_spark=use_spark)
    spatial_analyzer._build_grid()
    spatial_analyzer.build_od_matrix()
    spatial_analyzer.find_hotspots("start")
    spatial_analyzer.net_flow_analysis()
    log.info("空间分析器就绪")

    log.info("Web 看板数据初始化完成!")


# ================================================================
# 私有数据获取函数（每个API端点对应一个）
# ================================================================

def _get_kpis():
    """KPI 指标卡片"""
    ta = temporal_analyzer
    if ta.hourly_stats is None:
        ta.hourly_trip_count()
    if ta.peak_info is None:
        ta.identify_peak_hours()

    total_trips = len(ta.df)
    total_vehicles = ta.df["VehicleNum"].nunique()
    avg_duration = ta.df["duration_min"].mean()
    peak_hour = ta.peak_info.get("peak_hour_max", 0)
    peak_trips = ta.peak_info.get("peak_max_trips", 0)

    return [
        {"label": "总出行量", "value": f"{total_trips:,}"},
        {"label": "活跃车辆", "value": f"{total_vehicles:,}"},
        {"label": "平均时长", "value": f"{avg_duration:.1f} 分钟"},
        {"label": "高峰时段", "value": f"{int(peak_hour)}:00"},
        {"label": "高峰出行量", "value": f"{peak_trips:,}"},
    ]


def _get_hourly_data():
    """24小时出行量分布"""
    ta = temporal_analyzer
    if ta.hourly_stats is None:
        ta.hourly_trip_count()
    hourly = ta.hourly_stats
    return {
        "hours": [f"{h:02d}:00" for h in hourly["hour"]],
        "values": [int(v) for v in hourly["trip_count"].tolist()],
    }


def _get_duration_data():
    """行程时长分布（7段）"""
    ta = temporal_analyzer
    dur_stats = ta.duration_distribution()
    segments = dur_stats.get("segments", {})
    return {
        "labels": list(segments.keys()),
        "values": list(segments.values()),
    }


def _get_period_data():
    """4时段占比"""
    ta = temporal_analyzer
    period_stats = ta.period_analysis()
    return {
        "labels": period_stats["时段"].tolist(),
        "values": [round(v, 1) for v in period_stats["占比(%)"].tolist()],
    }


def _get_hotspot_data():
    """Top-15 出行热点"""
    sa = spatial_analyzer
    if sa.hotspots is None:
        sa.find_hotspots("start")
    hotspots = sa.hotspots.head(15)
    return {
        "labels": [
            f"#{int(r['cluster_id'])} ({r['center_lng']:.3f},{r['center_lat']:.3f})"
            for _, r in hotspots.iterrows()
        ],
        "values": [int(v) for v in hotspots["count"].tolist()],
    }


def _get_distance_data():
    """行程距离分布（NEW）"""
    ta = temporal_analyzer
    df = ta.df

    # 自定义分箱
    bins = [0, 1, 3, 5, 10, 20, 30, float("inf")]
    labels = ["<1km", "1-3km", "3-5km", "5-10km", "10-20km", "20-30km", ">30km"]

    dist = df["distance_km"]
    binned = pd.cut(dist, bins=bins, labels=labels, right=True)
    counts = binned.value_counts().reindex(labels, fill_value=0)

    # 统计指标
    stats = ta.distance_distribution()

    return {
        "labels": list(counts.index),
        "values": [int(v) for v in counts.values],
        "mean": round(float(dist.mean()), 2),
        "median": round(float(dist.median()), 2),
        "short_ratio": round(stats.get("short_trip_ratio", 0), 1),
        "long_ratio": round(stats.get("long_trip_ratio", 0), 1),
    }


def _get_speed_data():
    """行程速度分布（NEW）"""
    ta = temporal_analyzer
    df = ta.df

    bins = [0, 10, 20, 30, 40, 50, 60, 80, float("inf")]
    labels = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60-80", ">80"]

    speed = df["avg_speed"]
    binned = pd.cut(speed, bins=bins, labels=labels, right=True)
    counts = binned.value_counts().reindex(labels, fill_value=0)

    return {
        "labels": list(counts.index),
        "values": [int(v) for v in counts.values],
        "mean": round(float(speed.mean()), 1),
        "median": round(float(speed.median()), 1),
        "total": int(len(df)),
    }


def _get_vehicle_data():
    """车辆运营效率 Top-15（NEW）"""
    ta = temporal_analyzer
    eff = ta.vehicle_efficiency().head(15)

    vehicles = []
    for _, row in eff.iterrows():
        vehicles.append({
            "id": int(row["VehicleNum"]),
            "trips": int(row["trip_count"]),
            "total_dur": round(float(row["total_duration"]), 1),
            "total_dist": round(float(row["total_distance"]), 2),
            "avg_dur": round(float(row["avg_duration"]), 1),
            "avg_dist": round(float(row["avg_distance"]), 2),
        })

    return {"vehicles": vehicles}


def _get_od_flow_data():
    """
    OD流向数据 — 供 **深圳地图OD流向图** 使用
    使用 ECharts graph + geo 系列（参考 project_info/rule.md 地理坐标图）。

    返回:
      nodes: [{name, value: [lng, lat]}, ...]   # graph data 格式
      edges: [{source: name, target: name}, ...]  # graph edges 格式
    """
    sa = spatial_analyzer
    if sa.grid_od_matrix is None:
        sa.build_od_matrix()

    top_pairs = sa.top_od_pairs(30)

    # 收集原始 OD 对
    node_coords = {}
    raw_pairs = []
    for _, row in top_pairs.iterrows():
        o_lng, o_lat = round(float(row["O_lng"]), 5), round(float(row["O_lat"]), 5)
        d_lng, d_lat = round(float(row["D_lng"]), 5), round(float(row["D_lat"]), 5)
        o_name = f"({o_lng},{o_lat})"
        d_name = f"({d_lng},{d_lat})"
        node_coords[o_name] = [o_lng, o_lat]
        node_coords[d_name] = [d_lng, d_lat]
        raw_pairs.append({
            "source": o_name,
            "target": d_name,
            "value": int(row["flow"]),
        })

    # 合并双向流 (A→B vs B→A)，保留净值方向
    pair_map = {}
    for p in raw_pairs:
        key = (p["source"], p["target"])
        rev_key = (p["target"], p["source"])
        if rev_key in pair_map:
            rev = pair_map.pop(rev_key)
            net = p["value"] - rev["value"]
            if net > 0:
                pair_map[key] = {"source": p["source"], "target": p["target"], "value": net}
            elif net < 0:
                pair_map[rev_key] = {"source": rev["source"], "target": rev["target"], "value": -net}
        else:
            pair_map[key] = p

    clean_pairs = list(pair_map.values())

    # 构建节点列表 — graph series data 格式: {name, value: [lng, lat]}
    used = set()
    for p in clean_pairs:
        used.add(p["source"])
        used.add(p["target"])

    nodes = [{"name": n, "value": node_coords[n]} for n in sorted(used)]

    # 构建边列表 — graph series edges 格式: {source: name, target: name}
    edges = [{"source": p["source"], "target": p["target"]} for p in clean_pairs]

    return {
        "nodes": nodes,
        "edges": edges,
    }


def _get_net_flow_data():
    """
    区域净流入/流出（NEW）
    取 Top 15 净流入 + Top 15 净流出
    """
    sa = spatial_analyzer
    if sa.grid_od_matrix is None:
        sa.build_od_matrix()

    flow_df = sa.net_flow_analysis()

    # Top 15 净流入（正值最大）
    top_in = flow_df.nlargest(15, "net_flow")
    # Top 15 净流出（负值最大，即流出最多）
    top_out = flow_df.nsmallest(15, "net_flow")

    def format_label(row):
        return f"({row['lng']:.3f},{row['lat']:.3f})"

    return {
        "in_labels": [format_label(r) for _, r in top_in.iterrows()],
        "in_values": [int(r["net_flow"]) for _, r in top_in.iterrows()],
        "out_labels": [format_label(r) for _, r in top_out.iterrows()],
        "out_values": [int(abs(r["net_flow"])) for _, r in top_out.iterrows()],
    }


# ================================================================
# API 路由
# ================================================================

@app.route("/")
def index():
    """主页面 — Jinja2 模板渲染"""
    return render_template("index.html")


# --- 细粒度API（10个） ---

@app.route("/api/kpis")
def api_kpis():
    return jsonify(_get_kpis())


@app.route("/api/hourly")
def api_hourly():
    return jsonify(_get_hourly_data())


@app.route("/api/duration")
def api_duration():
    return jsonify(_get_duration_data())


@app.route("/api/period")
def api_period():
    return jsonify(_get_period_data())


@app.route("/api/hotspots")
def api_hotspots():
    return jsonify(_get_hotspot_data())


@app.route("/api/distance")
def api_distance():
    return jsonify(_get_distance_data())


@app.route("/api/speed")
def api_speed():
    return jsonify(_get_speed_data())


@app.route("/api/vehicles")
def api_vehicles():
    return jsonify(_get_vehicle_data())


@app.route("/api/od-flows")
def api_od_flows():
    return jsonify(_get_od_flow_data())


@app.route("/api/net-flow")
def api_net_flow():
    return jsonify(_get_net_flow_data())


# --- 聚合API（向后兼容） ---

@app.route("/api/dashboard")
def api_dashboard():
    """聚合所有数据 — 与旧版兼容，额外返回新图表数据"""
    return jsonify({
        "kpis": _get_kpis(),
        "hourly": _get_hourly_data(),
        "duration": _get_duration_data(),
        "period": _get_period_data(),
        "hotspots": _get_hotspot_data(),
        "distance": _get_distance_data(),
        "speed": _get_speed_data(),
        "vehicles": _get_vehicle_data(),
        "od_flows": _get_od_flow_data(),
        "net_flow": _get_net_flow_data(),
    })


@app.route("/api/health")
def health():
    """健康检查"""
    return jsonify({"status": "ok", "message": "服务运行正常"})


# ================================================================
# 实时大屏 API (MySQL数据源)
# ================================================================

import pymysql
import json


def _get_mysql_conn():
    """
    获取 MySQL 连接

    支持多种认证方式，自动处理 caching_sha2_password 认证问题。
    如果缺少 cryptography 包，将给出明确提示。
    """
    from src.config import MYSQL_CONFIG

    config = MYSQL_CONFIG.copy()

    # 尝试多种认证方式
    auth_configs = [
        {},  # 默认: 由 PyMySQL 自动协商
    ]

    # 如果 cryptography 可用，添加 caching_sha2_password 支持
    try:
        import cryptography  # noqa: F401
        # cryptography 可用，默认配置即可
    except ImportError:
        # 尝试使用 mysql_native_password 回退
        auth_configs.append({
            "auth_plugin_map": {"caching_sha2_password": None},
        })
        log.warning(
            "cryptography 包未安装，尝试使用 mysql_native_password 认证。\n"
            "  建议运行: pip install cryptography"
        )

    last_error = None
    for auth_opts in auth_configs:
        try:
            cfg = {**config, **auth_opts}
            conn = pymysql.connect(**cfg)
            return conn
        except Exception as e:
            last_error = e
            continue

    # 全部失败
    raise ConnectionError(
        f"MySQL 连接失败 ({config['host']}:{config['port']}): {last_error}\n"
        f"  请检查:\n"
        f"  1. CentOS VM MySQL 是否运行\n"
        f"  2. pip install cryptography\n"
        f"  3. 用户 '{config['user']}' 的认证插件是否为 mysql_native_password\n"
        f"     ALTER USER '{config['user']}'@'%' IDENTIFIED WITH mysql_native_password BY '{config['password']}'"
    )


@app.route("/realtime")
def realtime():
    """实时运行态势大屏"""
    return render_template("realtime.html")


@app.route("/api/realtime/kpis")
def api_realtime_kpis():
    """实时KPI指标 — 从MySQL读取"""
    try:
        conn = _get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='kpi_summary' AND stat_key='all'"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return jsonify(json.loads(row[0]))
        return jsonify({})
    except Exception as e:
        log.error(f"实时KPI查询失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/realtime/heatmap")
def api_realtime_heatmap():
    """热力图数据 — 从MySQL读取"""
    try:
        conn = _get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='heatmap_data' AND stat_key='all'"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            data = json.loads(row[0])
            return jsonify({"data": data})
        return jsonify({"data": []})
    except Exception as e:
        log.error(f"热力图查询失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/realtime/ranking")
def api_realtime_ranking():
    """上车热点排行 — 从MySQL读取"""
    try:
        conn = _get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='hotspot_ranking' AND stat_key='top15'"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            data = json.loads(row[0])
            return jsonify({"ranking": data})
        return jsonify({"ranking": []})
    except Exception as e:
        log.error(f"排行查询失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/realtime/trend")
def api_realtime_trend():
    """趋势数据 — 从MySQL读取"""
    try:
        conn = _get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='trend_data' AND stat_key='hourly'"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return jsonify(json.loads(row[0]))
        return jsonify({})
    except Exception as e:
        log.error(f"趋势查询失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/realtime/period")
def api_realtime_period():
    """时段对比数据"""
    try:
        conn = _get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stat_key, stat_value FROM realtime_stats WHERE stat_type='period_trips' ORDER BY id"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        labels, values = [], []
        for r in rows:
            labels.append(r[0])
            values.append(int(r[1]))
        return jsonify({"labels": labels, "values": values})
    except Exception as e:
        log.error(f"时段查询失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/realtime/hourly")
def api_realtime_hourly():
    """24小时出行量分布"""
    try:
        conn = _get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stat_key, stat_value FROM realtime_stats WHERE stat_type='hourly_trips' ORDER BY stat_key"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        hours, values = [], []
        for r in rows:
            hours.append(r[0])
            values.append(int(r[1]))
        return jsonify({"hours": hours, "values": values})
    except Exception as e:
        log.error(f"24小时查询失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/realtime/dashboard")
def api_realtime_dashboard():
    """聚合所有实时数据"""
    try:
        conn = _get_mysql_conn()
        cursor = conn.cursor()

        result = {}

        # KPI
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='kpi_summary' AND stat_key='all'"
        )
        row = cursor.fetchone()
        if row:
            result["kpis"] = json.loads(row[0])

        # 热力图
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='heatmap_data' AND stat_key='all'"
        )
        row = cursor.fetchone()
        if row:
            result["heatmap"] = json.loads(row[0])

        # 排行
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='hotspot_ranking' AND stat_key='top15'"
        )
        row = cursor.fetchone()
        if row:
            result["ranking"] = json.loads(row[0])

        # 趋势
        cursor.execute(
            "SELECT extra_info FROM realtime_stats WHERE stat_type='trend_data' AND stat_key='hourly'"
        )
        row = cursor.fetchone()
        if row:
            result["trend"] = json.loads(row[0])

        # 时段
        cursor.execute(
            "SELECT stat_key, stat_value FROM realtime_stats WHERE stat_type='period_trips' ORDER BY id"
        )
        rows = cursor.fetchall()
        result["period"] = {
            "labels": [r[0] for r in rows],
            "values": [int(r[1]) for r in rows],
        }

        # 24小时
        cursor.execute(
            "SELECT stat_key, stat_value FROM realtime_stats WHERE stat_type='hourly_trips' ORDER BY stat_key"
        )
        rows = cursor.fetchall()
        result["hourly"] = {
            "hours": [r[0] for r in rows],
            "values": [int(r[1]) for r in rows],
        }

        cursor.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        log.error(f"聚合查询失败: {e}")
        return jsonify({"error": str(e)}), 500


def _get_lan_ip():
    """获取本机局域网 IPv4 地址列表 (自动排除 VMware/VPN/Radmin 等虚拟网卡)"""
    import socket
    import subprocess
    import re
    import platform
    ips = []

    # 虚拟网卡关键词 (不区分大小写匹配)
    VIRTUAL_KEYWORDS = [
        'vmware', 'virtualbox', 'hyper-v', 'vethernet',
        'wsl', 'virtual', 'tap-', 'radmin', 'vpn',
        'loopback', 'bluetooth', 'teredo', 'tunnel',
    ]

    try:
        if platform.system() == 'Windows':
            # Windows: PowerShell 输出结构化数据，原生 UTF-8
            ps_cmd = (
                'Get-NetIPAddress -AddressFamily IPv4 | '
                'Select-Object IPAddress, InterfaceAlias | '
                'ConvertTo-Csv -NoTypeInformation'
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_cmd],
                capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            for line in result.stdout.split('\n'):
                line = line.strip().strip('"')
                if not line or 'IPAddress' in line or not re.search(r'\d\.', line):
                    continue
                # 格式: "IP","InterfaceAlias"
                parts = [p.strip('"') for p in line.split('","')]
                if len(parts) >= 2:
                    ip, alias = parts[0], parts[1]
                    is_virtual = any(kw in alias.lower() for kw in VIRTUAL_KEYWORDS)
                    if (not is_virtual and
                        not ip.startswith('127.') and
                        not ip.startswith('169.254.')):
                        if ip not in ips:
                            ips.append(ip)
        else:
            # Linux/Mac: 用 ip addr
            try:
                result = subprocess.run(
                    ['ip', '-4', 'addr', 'show'],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and '127.0.0.1' not in line:
                        m = re.search(
                            r'inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line
                        )
                        if m and not m.group(1).startswith('169.254.'):
                            ips.append(m.group(1))
            except Exception:
                pass

        # 回退: 标准 socket 方法 (无法区分虚拟网卡，但至少给个 IP)
        if not ips:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if (not ip.startswith('127.') and
                    not ip.startswith('169.254.') and
                    ip != '0.0.0.0'):
                    if ip not in ips:
                        ips.append(ip)

    except Exception:
        pass

    # 最后备选: UDP 探测获取实际路由出口 IP
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(('8.8.8.8', 53))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith('127.') and ip not in ips:
                ips.append(ip)
        except Exception:
            pass

    return ips


# ================================================================
# 启动
# ================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Flask Web 服务")
    parser.add_argument("--spark", action="store_true", help="使用 PySpark 分析引擎")
    args, _ = parser.parse_known_args()

    print("=" * 60)
    mode_label = "PySpark" if args.spark else "Pandas"
    print(f"  城市出行数据分析系统 - Flask Web 服务 ({mode_label} 引擎)")
    print("  shine 主题 | ECharts 5.5 | Leaflet 地图 | MySQL 数据源")
    print("=" * 60)

    # 预加载数据
    init_data(use_spark=args.spark)

    # 显示访问地址
    lan_ips = _get_lan_ip()
    print(f"\n  [Access] 访问地址:")
    print(f"  |-- 本机访问: http://localhost:{FLASK_PORT}")
    print(f"  |-- 分析看板: http://localhost:{FLASK_PORT}/")
    print(f"  |-- 实时大屏: http://localhost:{FLASK_PORT}/realtime")
    if lan_ips:
        print(f"\n  [LAN] 局域网访问 (同局域网设备):")
        for ip in lan_ips:
            print(f"  |-- http://{ip}:{FLASK_PORT}/        (分析看板)")
            print(f"  |-- http://{ip}:{FLASK_PORT}/realtime (实时大屏)")
    else:
        print(f"\n  [WARN] 未检测到局域网IP，仅限本机访问")
    print()

    # 启动时尝试测试 MySQL 连接 (非阻塞)
    try:
        conn = _get_mysql_conn()
        conn.close()
        print("  [OK] MySQL 连接正常 (192.168.116.128:3306)")
    except Exception as e:
        print(f"  [WARN] MySQL 连接失败: {e}")
        print("       实时大屏的 MySQL 数据源将不可用，但分析看板正常")
    print()

    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
    )
