# -*- coding: utf-8 -*-
"""
项目主入口文件
支持多种运行模式:
  - 命令行模式: python main.py
  - Web看板模式: python main.py --web
  - 数据清洗模式: python main.py --clean
  - 分析报告模式: python main.py --report
"""

import os
import sys
import time
import argparse
import traceback

# 添加项目路径
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PROJECT_DIR)


def _find_venv_python():
    """
    自动检测可用的虚拟环境 Python 解释器。
    优先查找 .venv_py38 (Python 3.8.10)，其次 .venv。
    返回 (python_exe_path, venv_name) 或 (None, None)。
    """
    candidates = [
        (".venv_py38", "Python 3.8.10"),
        (".venv", "Python 3.12"),
    ]
    for venv_name, label in candidates:
        if os.name == "nt":
            exe = os.path.join(_PROJECT_DIR, venv_name, "Scripts", "python.exe")
        else:
            exe = os.path.join(_PROJECT_DIR, venv_name, "bin", "python")
        if os.path.isfile(exe):
            return exe, venv_name
    return None, None


def _relaunch_with_venv():
    """
    如果当前 Python 缺少 Flask，自动查找并使用项目虚拟环境重新启动。
    """
    venv_exe, venv_name = _find_venv_python()
    if venv_exe is None:
        return False

    # 检查 venv 中是否有 Flask
    import subprocess
    try:
        result = subprocess.run(
            [venv_exe, "-c", "import flask"],
            capture_output=True, timeout=10
        )
        if result.returncode != 0:
            return False
    except Exception:
        return False

    # 重新以 venv Python 执行当前脚本，传递相同参数
    print(f"[INFO] 检测到虚拟环境: {venv_name}")
    print(f"[INFO] 重新启动: {venv_exe} {' '.join(sys.argv)}")
    print()
    sys.stdout.flush()
    # 使用 subprocess.call 替代 os.execv (Windows 兼容性更好)
    sys.exit(subprocess.call([venv_exe] + sys.argv))
    return True  # 不会执行到这里

from src.config import RAW_DATA_PATH, CLEANED_DATA_PATH, FIGURES_DIR, REPORTS_DIR, LOG_DIR
from src.logger import setup_logger, get_logger
from src.data_loader import DataLoader
from src.data_cleaner import DataCleaner
from src.temporal_analysis import TemporalAnalyzer
from src.spatial_analysis import SpatialAnalyzer
from src.visualization import Visualizer

# 初始化日志
os.makedirs(LOG_DIR, exist_ok=True)
log = setup_logger("taxi_analysis")


def ensure_dirs():
    """确保必要的目录存在"""
    for d in [FIGURES_DIR, REPORTS_DIR]:
        os.makedirs(d, exist_ok=True)


def run_data_cleaning():
    """执行数据清洗流水线"""
    log.section("模式: 数据清洗流水线")
    start_time = time.time()

    loader = DataLoader()
    cleaner = DataCleaner()

    try:
        # 加载原始数据
        raw_df = loader.load_raw_data()
        log.info(f"原始数据加载完成: {len(raw_df):,} 条记录, {len(raw_df.columns)} 个字段")

        # 生成清洗前质量报告
        loader.generate_quality_report(raw_df)

        # 执行清洗流水线
        cleaned_df = cleaner.run_pipeline(raw_df)
        log.info(f"清洗流水线完成: {len(cleaned_df):,} 条有效行程")

        # 导出到 tax_data/taxi_sz.csv (覆盖原文件)
        output_path = CLEANED_DATA_PATH
        cleaner.export_cleaned_data(cleaned_df, output_path)
        log.info(f"清洗数据已导出: {output_path}")

        # 打印清洗报告
        report = cleaner.get_cleaning_report()
        log.info(report)

    except Exception as e:
        log.error(f"数据清洗失败: {e}")
        log.error(traceback.format_exc())
        raise

    elapsed = time.time() - start_time
    log.info(f"数据清洗总耗时: {elapsed:.2f}秒")
    log.info(f"日志文件: {log.get_log_file()}")

    return cleaned_df


def run_analysis(df=None):
    """执行完整分析"""
    log.section("模式: 数据分析")
    start_time = time.time()

    ensure_dirs()

    # 加载数据
    loader = DataLoader()
    if df is None:
        df = loader.load_cleaned_data()

    log.info(f"分析数据: {len(df):,} 条行程, {len(df.columns)} 个字段")

    try:
        loader.generate_od_report(df)

        # 时序分析
        log.section("时序分析")
        temporal = TemporalAnalyzer(df)
        temporal.hourly_trip_count()
        temporal.identify_peak_hours()
        temporal.duration_distribution()
        temporal.distance_distribution()
        temporal.period_analysis()
        efficiency = temporal.vehicle_efficiency()

        # 空间分析
        log.section("空间分析")
        spatial = SpatialAnalyzer(df)
        spatial._build_grid()
        spatial.build_od_matrix()
        spatial.find_hotspots("start")
        spatial.find_hotspots("end")
        spatial.net_flow_analysis()

        # 可视化
        log.section("可视化")
        viz = Visualizer()
        viz.set_analyzers(temporal, spatial)

        # 时序图表
        viz.hourly_trip_chart()
        viz.duration_histogram()
        viz.scatter_duration_distance()

        # 空间图表
        density = spatial.trip_density("start")
        viz.heatmap_map(density, "出行起点热力分布", "heatmap_start.html")

        if spatial.hotspots is not None:
            viz.hotspot_bar_chart()

        # 综合看板
        viz.create_dashboard()

        # 生成分析报告
        generate_report(temporal, spatial, efficiency)

    except Exception as e:
        log.error(f"数据分析失败: {e}")
        log.error(traceback.format_exc())
        raise

    elapsed = time.time() - start_time
    log.info(f"[完成] 所有分析已完成! 总耗时: {elapsed:.2f}秒")
    log.info(f"[完成] 图表输出目录: {FIGURES_DIR}")
    log.info(f"[完成] 报告输出目录: {REPORTS_DIR}")
    log.info(f"[完成] 日志文件: {log.get_log_file()}")


def generate_report(temporal, spatial, efficiency):
    """生成Markdown分析报告"""
    log.info("正在生成分析报告...")

    df = temporal.df
    total_trips = len(df)

    # 安全获取统计值
    avg_duration = df["duration_min"].mean() if "duration_min" in df.columns else 0
    avg_distance = df["distance_km"].mean() if "distance_km" in df.columns else 0
    short_trip_ratio = (df["distance_km"] < 3).mean() * 100 if "distance_km" in df.columns else 0
    long_trip_ratio = (df["distance_km"] > 10).mean() * 100 if "distance_km" in df.columns else 0

    lines = [
        "# 深圳市出租车出行行为分析报告",
        "",
        f"## 1. 数据概览",
        f"- 总出行量: {total_trips:,} 次",
        f"- 活跃车辆数: {df['VehicleNum'].nunique():,} 辆",
        f"- 平均行程时长: {avg_duration:.1f} 分钟",
        f"- 平均行程距离: {avg_distance:.2f} km",
        "",
        f"## 2. 出行高峰",
    ]

    if temporal.peak_info:
        pi = temporal.peak_info
        lines.append(f"- 早高峰: {pi.get('morning_peak', [])}")
        lines.append(f"- 晚高峰: {pi.get('evening_peak', [])}")
        lines.append(f"- 极值高峰小时: {pi.get('peak_hour_max')}:00 "
                     f"({pi.get('peak_max_trips', 0):,}次)")

    lines.extend([
        "",
        "## 3. 出行特征",
        f"- 短途出行(<3km)占比: {short_trip_ratio:.1f}%",
        f"- 长途出行(>10km)占比: {long_trip_ratio:.1f}%",
        "",
        "## 4. 空间分析",
        f"- 热点区域数量: {len(spatial.hotspots) if spatial.hotspots is not None else 0}",
        "",
        "## 5. 运营效率 Top-5",
    ])

    if efficiency is not None:
        for _, row in efficiency.head(5).iterrows():
            lines.append(f"- {row['VehicleNum']}: {int(row['trip_count'])}次, "
                         f"均长{row['avg_duration']:.1f}分钟")

    lines.extend([
        "",
        "---",
        "*报告由城市出行数据分析系统自动生成*",
    ])

    report_path = os.path.join(REPORTS_DIR, "analysis_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log.info(f"分析报告已保存: {report_path}")


def _get_lan_ips():
    """获取本机局域网 IPv4 地址列表"""
    import socket
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if (not ip.startswith('127.') and
                not ip.startswith('169.254.') and
                ip != '0.0.0.0'):
                if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                    if ip not in ips:
                        ips.append(ip)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(('192.168.116.128', 1))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith('127.') and ip not in ips:
                ips.append(ip)
        except Exception:
            pass
    return ips


def run_web():
    """启动Web看板"""
    # 检查 Flask 是否可用，不可用则尝试自动切换到项目 venv
    try:
        import flask  # noqa: F401
    except ImportError:
        if not _relaunch_with_venv():
            print("[ERROR] Flask 未安装! 请激活虚拟环境后重试:")
            print("  .venv_py38\\Scripts\\activate")
            print("  python main.py --web")
            sys.exit(1)
        return  # _relaunch_with_venv 成功后不会返回

    from src.web_app import app, FLASK_HOST, FLASK_PORT, FLASK_DEBUG
    from src.web_app import init_data

    log.section("模式: Web看板")
    log.info("正在初始化数据...")
    init_data()

    # 显示本机访问地址
    log.info(f"本机访问: http://localhost:{FLASK_PORT}")
    log.info(f"实时大屏: http://localhost:{FLASK_PORT}/realtime")

    # 显示局域网访问地址
    lan_ips = _get_lan_ips()
    if lan_ips:
        log.info("--- 局域网访问地址 (同局域网设备) ---")
        for ip in lan_ips:
            log.info(f"  http://{ip}:{FLASK_PORT}/         (分析看板)")
            log.info(f"  http://{ip}:{FLASK_PORT}/realtime  (实时大屏)")
    else:
        log.info("⚠ 未检测到局域网IP，仅限本机访问")
    log.info(f"日志文件: {log.get_log_file()}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)


# ----------------------------------------------------------
# 命令行入口
# ----------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="城市出行数据分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行示例:
  python main.py              # 默认: 执行完整分析
  python main.py --clean      # 仅数据清洗
  python main.py --web        # 启动Web看板
  python main.py --report     # 仅生成报告
        """,
    )
    parser.add_argument("--clean", action="store_true", help="仅执行数据清洗")
    parser.add_argument("--web", action="store_true", help="启动Flask Web看板")
    parser.add_argument("--report", action="store_true", help="仅生成分析报告")

    args = parser.parse_args()

    if args.clean:
        run_data_cleaning()
    elif args.web:
        run_web()
    elif args.report:
        run_analysis()
    else:
        # 默认: 完整分析
        run_analysis()
