# -*- coding: utf-8 -*-
"""
项目主入口文件
支持多种运行模式:
  - 命令行模式: python main.py
  - PySpark模式: python main.py --spark        (使用VM Spark集群计算)
  - Web看板模式: python main.py --web
  - 数据清洗模式: python main.py --clean
  - MySQL上传:   python main.py --upload        (上传分析结果到MySQL)
  - 一键全流程:  python main.py --spark --upload  (清洗→分析→上传)
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
    """如果当前 Python 缺少 Flask，自动查找并使用项目虚拟环境重新启动。"""
    venv_exe, venv_name = _find_venv_python()
    if venv_exe is None:
        return False

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

    print(f"[INFO] 检测到虚拟环境: {venv_name}")
    print(f"[INFO] 重新启动: {venv_exe} {' '.join(sys.argv)}")
    print()
    sys.stdout.flush()
    sys.exit(subprocess.call([venv_exe] + sys.argv))
    return True


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

# 全局变量
_spark_started = False


def ensure_dirs():
    """确保必要的目录存在"""
    for d in [FIGURES_DIR, REPORTS_DIR]:
        os.makedirs(d, exist_ok=True)


def init_spark():
    """初始化 PySpark 会话 (连接 VM 或本地)"""
    global _spark_started
    if _spark_started:
        return True

    from src.spark_manager import get_spark, is_spark_available

    spark = get_spark()
    if spark is not None:
        _spark_started = True
        log.info(f"PySpark 已就绪 (模式: {spark.sparkContext.master})")
        return True
    else:
        log.warning("PySpark 不可用，将使用 Pandas 处理")
        return False


def upload_to_mysql(cleaned_df=None, hourly_df=None, period_df=None,
                    hotspots_df=None, efficiency_df=None, flow_df=None,
                    kpis=None):
    """上传分析结果到 MySQL (CentOS VM)"""
    from src.mysql_uploader import MySQLUploader

    log.section("MySQL 上传")
    uploader = MySQLUploader()
    try:
        uploader.upload_all(
            cleaned_df=cleaned_df,
            hourly_df=hourly_df,
            period_df=period_df,
            hotspots_df=hotspots_df,
            efficiency_df=efficiency_df,
            flow_df=flow_df,
            kpis=kpis,
        )
        log.info("MySQL 上传成功!")
        return True
    except Exception as e:
        log.error(f"MySQL 上传失败: {e}")
        log.error(traceback.format_exc())
        return False


def run_data_cleaning(use_spark=False, upload=False):
    """执行数据清洗流水线"""
    log.section("模式: 数据清洗流水线")
    start_time = time.time()

    if use_spark:
        log.info("使用 PySpark 模式进行数据清洗")
        init_spark()

    loader = DataLoader()
    cleaner = DataCleaner(use_spark=use_spark)

    try:
        # 加载原始数据
        raw_df = loader.load_raw_data()
        log.info(f"原始数据加载完成: {len(raw_df):,} 条记录, {len(raw_df.columns)} 个字段")

        # 生成清洗前质量报告
        loader.generate_quality_report(raw_df)

        # 执行清洗流水线
        cleaned_df = cleaner.run_pipeline(raw_df)
        log.info(f"清洗流水线完成: {len(cleaned_df):,} 条有效行程")

        # 导出到 tax_data/taxi_sz.csv
        output_path = CLEANED_DATA_PATH
        cleaner.export_cleaned_data(cleaned_df, output_path)
        log.info(f"清洗数据已导出: {output_path}")

        # 打印清洗报告
        report = cleaner.get_cleaning_report()
        log.info(report)

        # 上传到 MySQL (放在 try 内部以便捕获异常)
        if upload:
            log.info("开始上传清洗结果到 MySQL...")
            upload_to_mysql(cleaned_df=cleaned_df)

    except Exception as e:
        log.error(f"数据清洗失败: {e}")
        log.error(traceback.format_exc())
        raise

    elapsed = time.time() - start_time
    log.info(f"数据清洗总耗时: {elapsed:.2f}秒")
    log.info(f"日志文件: {log.get_log_file()}")

    return cleaned_df


def run_analysis(df=None, use_spark=False, upload=False):
    """执行完整分析"""
    log.section("模式: 数据分析")
    start_time = time.time()

    if use_spark:
        log.info("使用 PySpark 模式进行数据分析")
        init_spark()

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
        temporal = TemporalAnalyzer(df, use_spark=use_spark)
        hourly_df = temporal.hourly_trip_count()
        peak_info = temporal.identify_peak_hours()
        temporal.duration_distribution()
        temporal.distance_distribution()
        period_df = temporal.period_analysis()
        efficiency = temporal.vehicle_efficiency()

        # 空间分析
        log.section("空间分析")
        spatial = SpatialAnalyzer(df, use_spark=use_spark)
        spatial._build_grid()
        spatial.build_od_matrix()
        spatial.find_hotspots("start")
        spatial.find_hotspots("end")
        flow_df = spatial.net_flow_analysis()

        # KPI 数据 (用于 MySQL 上传)
        kpis = [
            {"label": "总出行量", "value": f"{len(df):,}"},
            {"label": "活跃车辆", "value": f"{df['VehicleNum'].nunique():,}"},
            {"label": "平均时长", "value": f"{df['duration_min'].mean():.1f} 分钟"},
            {"label": "高峰时段", "value": f"{int(peak_info.get('peak_hour_max', 0))}:00"},
            {"label": "高峰出行量", "value": f"{int(peak_info.get('peak_max_trips', 0)):,}"},
        ]

        # 可视化
        log.section("可视化")
        viz = Visualizer()
        viz.set_analyzers(temporal, spatial)

        viz.hourly_trip_chart()
        viz.duration_histogram()
        viz.scatter_duration_distance()

        density = spatial.trip_density("start")
        viz.heatmap_map(density, "出行起点热力分布", "heatmap_start.html")

        if spatial.hotspots is not None:
            viz.hotspot_bar_chart()

        viz.create_dashboard()

        # 生成分析报告
        generate_report(temporal, spatial, efficiency)

        # 上传到 MySQL (放在 try 内部)
        if upload:
            log.info("开始上传分析结果到 MySQL...")
            upload_to_mysql(
                cleaned_df=df,
                hourly_df=hourly_df,
                period_df=period_df,
                hotspots_df=spatial.hotspots,
                efficiency_df=efficiency,
                flow_df=flow_df,
                kpis=kpis,
            )

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
    """生成 Markdown 分析报告"""
    log.info("正在生成分析报告...")

    df = temporal.df
    total_trips = len(df)

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
    import subprocess
    import re
    import platform
    ips = []

    VIRTUAL_KEYWORDS = [
        'vmware', 'virtualbox', 'hyper-v', 'vethernet',
        'wsl', 'virtual', 'tap-', 'radmin', 'vpn',
        'loopback', 'bluetooth', 'teredo', 'tunnel',
    ]

    try:
        if platform.system() == 'Windows':
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


def run_web():
    """启动 Web 看板"""
    try:
        import flask  # noqa: F401
    except ImportError:
        if not _relaunch_with_venv():
            print("[ERROR] Flask 未安装! 请激活虚拟环境后重试:")
            print("  .venv_py38\\Scripts\\activate")
            print("  python main.py --web")
            sys.exit(1)
        return

    from src.web_app import app, FLASK_HOST, FLASK_PORT, FLASK_DEBUG
    from src.web_app import init_data

    log.section("模式: Web看板")
    log.info("正在初始化数据...")
    init_data()

    log.info(f"本机访问: http://localhost:{FLASK_PORT}")
    log.info(f"实时大屏: http://localhost:{FLASK_PORT}/realtime")

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


def cleanup():
    """清理资源"""
    global _spark_started
    if _spark_started:
        from src.spark_manager import stop_spark
        stop_spark()
        _spark_started = False


# ----------------------------------------------------------
# 命令行入口
# ----------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="城市出行数据分析系统 (支持 PySpark + MySQL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行示例:
  python main.py                     # 默认: Pandas 模式执行完整分析
  python main.py --spark             # PySpark 模式 (VM集群优先→本机→回退)
  python main.py --spark --upload    # PySpark + 上传结果到 MySQL
  python main.py --clean --spark     # PySpark 模式仅数据清洗
  python main.py --upload            # 仅上传已有分析结果到 MySQL
  python main.py --web               # 启动 Flask Web 看板
  python main.py --report            # 仅生成分析报告

VM 连接: CentOS 7 (192.168.116.128:7077 Spark, :3306 MySQL)
        """,
    )
    parser.add_argument("--clean", action="store_true",
                        help="仅执行数据清洗")
    parser.add_argument("--web", action="store_true",
                        help="启动 Flask Web 看板")
    parser.add_argument("--report", action="store_true",
                        help="仅生成分析报告")
    parser.add_argument("--spark", action="store_true",
                        help="使用 PySpark (自动连接 VM 或本地多核)")
    parser.add_argument("--upload", action="store_true",
                        help="上传分析结果到 MySQL (CentOS VM)")
    parser.add_argument("--full", action="store_true",
                        help="一键全流程: 清洗→分析→可视化→上传MySQL")

    args = parser.parse_args()

    use_spark = args.spark or args.full
    do_upload = args.upload or args.full

    try:
        if args.clean:
            run_data_cleaning(use_spark=use_spark, upload=do_upload)
        elif args.web:
            run_web()
        elif args.report:
            run_analysis(use_spark=use_spark, upload=do_upload)
        elif args.full:
            # 一键全流程: 清洗 → 分析 → 上传
            cleaned = run_data_cleaning(use_spark=use_spark, upload=False)
            run_analysis(df=cleaned, use_spark=use_spark, upload=do_upload)
        elif args.upload:
            # 仅上传已有数据
            run_analysis(use_spark=False, upload=True)
        else:
            # 默认: 完整分析
            run_analysis(use_spark=use_spark, upload=do_upload)
    finally:
        cleanup()
