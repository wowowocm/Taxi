# -*- coding: utf-8 -*-
"""
MySQL 数据上传模块
将 PySpark/Pandas 分析结果上传到 CentOS VM 的 MySQL 数据库

数据库: taxi_analysis (192.168.116.128:3306)
用户: root / mysql123456

上传内容:
  - od_trips: 清洗后的 OD 行程数据
  - hourly_stats: 24小时出行量统计
  - period_stats: 时段统计
  - hotspots: 热点区域
  - vehicle_efficiency: 车辆运营效率
  - net_flow: 净流入流出
  - realtime_stats: Web 实时大屏缓存
"""

import time
import json
import traceback
import pandas as pd
import pymysql
from .config import MYSQL_CONFIG
from .logger import get_logger


class MySQLUploader:
    """MySQL 数据上传器"""

    # 每张表的期望列定义 (用于自动检测和修复 schema 不匹配)
    EXPECTED_SCHEMA = {
        "od_trips": {
            "columns": [
                ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
                ("VehicleNum", "INT NOT NULL"),
                ("Stime", "VARCHAR(8) NOT NULL COMMENT '出发时间 HH:MM:SS'"),
                ("SLng", "DOUBLE NOT NULL COMMENT '起点经度'"),
                ("SLat", "DOUBLE NOT NULL COMMENT '起点纬度'"),
                ("ELng", "DOUBLE NOT NULL COMMENT '终点经度'"),
                ("ELat", "DOUBLE NOT NULL COMMENT '终点纬度'"),
                ("Etime", "VARCHAR(8) NOT NULL COMMENT '到达时间 HH:MM:SS'"),
                ("duration_min", "DOUBLE COMMENT '行程时长(分钟)'"),
                ("distance_km", "DOUBLE COMMENT '行程距离(公里)'"),
                ("avg_speed", "DOUBLE COMMENT '平均速度(km/h)'"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ],
            "indexes": [
                "INDEX idx_vehicle (VehicleNum)",
                "INDEX idx_duration (duration_min)",
                "INDEX idx_distance (distance_km)",
            ],
        },
        "hourly_stats": {
            "columns": [
                ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
                ("hour", "INT NOT NULL COMMENT '小时 0-23'"),
                ("trip_count", "INT NOT NULL COMMENT '出行量'"),
                ("avg_duration", "DOUBLE COMMENT '平均时长(分钟)'"),
                ("median_duration", "DOUBLE COMMENT '中位时长(分钟)'"),
                ("avg_distance", "DOUBLE COMMENT '平均距离(km)'"),
                ("unique_vehicles", "INT COMMENT '活跃车辆数'"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ],
            "indexes": ["UNIQUE KEY uk_hour (hour)"],
        },
        "period_stats": {
            "columns": [
                ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
                ("period_name", "VARCHAR(20) NOT NULL COMMENT '时段名称'"),
                ("time_range", "VARCHAR(20) COMMENT '时间范围'"),
                ("trip_count", "INT NOT NULL COMMENT '出行量'"),
                ("ratio_pct", "DOUBLE COMMENT '占比(%)'"),
                ("avg_duration", "DOUBLE COMMENT '平均时长(分钟)'"),
                ("avg_distance", "DOUBLE COMMENT '平均距离(km)'"),
                ("active_vehicles", "INT COMMENT '活跃车辆数'"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ],
            "indexes": ["UNIQUE KEY uk_period (period_name)"],
        },
        "hotspots": {
            "columns": [
                ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
                ("cluster_id", "INT NOT NULL COMMENT '聚类ID'"),
                ("center_lng", "DOUBLE NOT NULL COMMENT '中心经度'"),
                ("center_lat", "DOUBLE NOT NULL COMMENT '中心纬度'"),
                ("trip_count", "INT NOT NULL COMMENT '出行量'"),
                ("radius_m", "DOUBLE COMMENT '半径(米)'"),
                ("point_type", "VARCHAR(10) DEFAULT 'start' COMMENT '起点/终点'"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ],
            "indexes": ["INDEX idx_count (trip_count)"],
        },
        "vehicle_efficiency": {
            "columns": [
                ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
                ("VehicleNum", "INT NOT NULL"),
                ("trip_count", "INT NOT NULL COMMENT '载客次数'"),
                ("total_duration", "DOUBLE COMMENT '总载客时长(分钟)'"),
                ("total_distance", "DOUBLE COMMENT '总载客距离(km)'"),
                ("avg_duration", "DOUBLE COMMENT '平均时长(分钟)'"),
                ("avg_distance", "DOUBLE COMMENT '平均距离(km)'"),
                ("first_trip", "VARCHAR(8) COMMENT '首班时间'"),
                ("last_trip", "VARCHAR(8) COMMENT '末班时间'"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ],
            "indexes": [
                "UNIQUE KEY uk_vehicle (VehicleNum)",
                "INDEX idx_trips (trip_count)",
            ],
        },
        "net_flow": {
            "columns": [
                ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
                ("grid_id", "INT NOT NULL COMMENT '网格ID'"),
                ("lng", "DOUBLE NOT NULL COMMENT '网格中心经度'"),
                ("lat", "DOUBLE NOT NULL COMMENT '网格中心纬度'"),
                ("outflow", "INT DEFAULT 0 COMMENT '流出量'"),
                ("inflow", "INT DEFAULT 0 COMMENT '流入量'"),
                ("net_flow", "INT DEFAULT 0 COMMENT '净流量(流入-流出)'"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ],
            "indexes": [
                "INDEX idx_net (net_flow)",
                "INDEX idx_grid (grid_id)",
            ],
        },
        "realtime_stats": {
            "columns": [
                ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
                ("stat_type", "VARCHAR(50) NOT NULL COMMENT '统计类型'"),
                ("stat_key", "VARCHAR(100) NOT NULL COMMENT '统计键'"),
                ("stat_value", "DOUBLE COMMENT '统计值'"),
                ("extra_info", "JSON COMMENT '额外信息(JSON)'"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ],
            "indexes": ["UNIQUE KEY uk_type_key (stat_type, stat_key)"],
        },
    }

    def __init__(self):
        self.log = get_logger()
        self._conn = None

    def get_connection(self):
        """获取 MySQL 连接"""
        if self._conn is not None and self._conn.open:
            try:
                self._conn.ping(reconnect=False)
                return self._conn
            except Exception:
                self._conn = None

        config = MYSQL_CONFIG.copy()
        last_error = None

        auth_configs = [{}]
        # 如果 cryptography 不可用，尝试兼容模式
        try:
            import cryptography  # noqa: F401
        except ImportError:
            auth_configs.append({"auth_plugin_map": {"caching_sha2_password": None}})
            self.log.warning("cryptography 未安装，尝试 mysql_native_password 认证。建议: pip install cryptography")

        for auth_opts in auth_configs:
            try:
                cfg = {**config, **auth_opts}
                self._conn = pymysql.connect(**cfg)
                self.log.info(f"MySQL 连接成功: {config['host']}:{config['port']}/{config['database']}")
                return self._conn
            except Exception as e:
                last_error = e
                continue

        raise ConnectionError(
            f"MySQL 连接失败 ({config['host']}:{config['port']}): {last_error}\n"
            f"  提示: pip install cryptography"
        )

    def close(self):
        """关闭连接"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ----------------------------------------------------------
    # 自动 Schema 检测 & 修复
    # ----------------------------------------------------------

    def _get_existing_columns(self, table_name: str) -> list:
        """
        获取 MySQL 中某张表的实际列名列表 (小写)

        Returns
        -------
        list[str]
            列名列表 (均为小写)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            rows = cursor.fetchall()
            return [r[0].lower() for r in rows]
        except Exception:
            return []
        finally:
            cursor.close()

    def _table_has_correct_schema(self, table_name: str) -> bool:
        """
        检查 MySQL 中已有的表是否与期望 schema 匹配

        匹配规则: 表的所有期望列都存在 (忽略大小写)
        """
        expected_schema = self.EXPECTED_SCHEMA.get(table_name)
        if expected_schema is None:
            return True  # 没有定义期望 schema，放过

        existing_cols = self._get_existing_columns(table_name)
        if not existing_cols:
            return False  # 表不存在

        expected_cols = [c[0].lower() for c in expected_schema["columns"]]

        # 检查每个期望列是否都在现有表中
        for ec in expected_cols:
            if ec not in existing_cols:
                self.log.warning(
                    f"表 {table_name} 缺少列 '{ec}'，"
                    f"现有列: {existing_cols}"
                )
                return False

        return True

    def _safe_drop_table(self, table_name: str):
        """安全删除表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            conn.commit()
            self.log.info(f"已删除旧表: {table_name}")
        except Exception as e:
            self.log.warning(f"删除表 {table_name} 失败: {e}")
        finally:
            cursor.close()

    def _create_table(self, table_name: str):
        """根据 EXPECTED_SCHEMA 创建表"""
        schema = self.EXPECTED_SCHEMA.get(table_name)
        if schema is None:
            self.log.warning(f"表 {table_name} 无预定义 schema，跳过创建")
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        col_defs = [f"`{c[0]}` {c[1]}" for c in schema["columns"]]
        index_defs = schema.get("indexes", [])

        all_defs = col_defs + index_defs
        ddl = f"CREATE TABLE `{table_name}` (\n  " + ",\n  ".join(all_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

        try:
            cursor.execute(ddl)
            conn.commit()
            self.log.info(f"表 {table_name} 创建成功 ({len(col_defs)} 列)")
        except Exception as e:
            self.log.error(f"创建表 {table_name} 失败: {e}")
            self.log.error(traceback.format_exc())
            raise
        finally:
            cursor.close()

    def ensure_tables(self):
        """
        确保所有数据库表存在且 schema 正确。

        逻辑:
          1. 先创建数据库（如果不存在）
          2. 逐表检查:
             - 表不存在 → 直接创建
             - 表存在但列不匹配 → DROP 后重建
             - 表存在且列匹配 → 跳过
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 确保数据库存在
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{MYSQL_CONFIG['database']}`")
        cursor.close()

        self.log.info("开始检查 MySQL 表结构...")

        for table_name in self.EXPECTED_SCHEMA:
            existing_cols = self._get_existing_columns(table_name)

            if not existing_cols:
                # 表不存在 → 创建
                self._create_table(table_name)
            elif not self._table_has_correct_schema(table_name):
                # 表存在但 schema 不匹配 → 删除后重建
                self.log.warning(
                    f"表 {table_name} schema 不匹配！"
                    f"现有列: {existing_cols}, "
                    f"期望列: {[c[0] for c in self.EXPECTED_SCHEMA[table_name]['columns']]}"
                )
                self._safe_drop_table(table_name)
                self._create_table(table_name)
            else:
                self.log.debug(f"表 {table_name} schema 正确，跳过")

        self.log.info("MySQL 表结构检查完成")

    # ----------------------------------------------------------
    # 上传方法
    # ----------------------------------------------------------

    def upload_od_trips(self, df: pd.DataFrame):
        """
        上传清洗后的 OD 行程数据 (全量替换)

        Parameters
        ----------
        df : pd.DataFrame
            含 VehicleNum, Stime, SLng, SLat, ELng, ELat, Etime,
            duration_min, distance_km, avg_speed
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        self.log.info(f"开始上传 OD 行程数据: {len(df):,} 条...")
        cursor.execute("TRUNCATE TABLE od_trips")

        batch_size = 1000
        total = len(df)
        inserted = 0
        errors = 0

        for start in range(0, total, batch_size):
            batch = df.iloc[start:start + batch_size]
            rows = []
            for _, row in batch.iterrows():
                try:
                    rows.append((
                        int(row["VehicleNum"]),
                        str(row["Stime"]),
                        float(row["SLng"]),
                        float(row["SLat"]),
                        float(row["ELng"]),
                        float(row["ELat"]),
                        str(row["Etime"]),
                        float(row.get("duration_min", 0)),
                        float(row.get("distance_km", 0)),
                        float(row.get("avg_speed", 0)),
                    ))
                except Exception as e:
                    errors += 1
                    self.log.warning(f"跳过异常行: {e}")

            if rows:
                cursor.executemany(
                    """INSERT INTO od_trips
                       (VehicleNum, Stime, SLng, SLat, ELng, ELat, Etime,
                        duration_min, distance_km, avg_speed)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    rows
                )
                conn.commit()
                inserted += len(rows)

            if (start // batch_size) % 5 == 0:
                self.log.info(f"  OD数据上传进度: {inserted:,}/{total:,}")

        cursor.close()
        self.log.info(f"OD 行程数据上传完成: {inserted:,} 条 (跳过 {errors} 条异常)")

    def upload_hourly_stats(self, hourly_df: pd.DataFrame):
        """上传24小时出行量统计"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("TRUNCATE TABLE hourly_stats")
        rows = []
        for _, row in hourly_df.iterrows():
            rows.append((
                int(row["hour"]),
                int(row["trip_count"]),
                float(row.get("avg_duration", 0)),
                float(row.get("median_duration", 0)),
                float(row.get("avg_distance", 0)),
                int(row.get("unique_vehicles", 0)),
            ))

        cursor.executemany(
            """INSERT INTO hourly_stats
               (hour, trip_count, avg_duration, median_duration, avg_distance, unique_vehicles)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE trip_count=VALUES(trip_count),
               avg_duration=VALUES(avg_duration), median_duration=VALUES(median_duration),
               avg_distance=VALUES(avg_distance), unique_vehicles=VALUES(unique_vehicles)""",
            rows
        )
        conn.commit()
        cursor.close()
        self.log.info(f"小时统计上传完成: {len(rows)} 条")

    def upload_period_stats(self, period_df: pd.DataFrame):
        """上传时段统计"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("TRUNCATE TABLE period_stats")
        rows = []
        for _, row in period_df.iterrows():
            rows.append((
                str(row["时段"]),
                str(row.get("时间范围", "")),
                int(row["出行量"]),
                float(row.get("占比(%)", 0)),
                float(row.get("平均时长(分钟)", 0)),
                float(row.get("平均距离(km)", 0)),
                int(row.get("活跃车辆数", 0)),
            ))

        cursor.executemany(
            """INSERT INTO period_stats
               (period_name, time_range, trip_count, ratio_pct, avg_duration, avg_distance, active_vehicles)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            rows
        )
        conn.commit()
        cursor.close()
        self.log.info(f"时段统计上传完成: {len(rows)} 条")

    def upload_hotspots(self, hotspots_df: pd.DataFrame, point_type: str = "start"):
        """上传热点区域"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("TRUNCATE TABLE hotspots")
        rows = []
        for _, row in hotspots_df.iterrows():
            rows.append((
                int(row["cluster_id"]),
                float(row["center_lng"]),
                float(row["center_lat"]),
                int(row["count"]),
                float(row.get("radius_m", 0)),
                point_type,
            ))

        cursor.executemany(
            """INSERT INTO hotspots
               (cluster_id, center_lng, center_lat, trip_count, radius_m, point_type)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            rows
        )
        conn.commit()
        cursor.close()
        self.log.info(f"热点区域上传完成: {len(rows)} 条")

    def upload_vehicle_efficiency(self, eff_df: pd.DataFrame):
        """上传车辆运营效率"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("TRUNCATE TABLE vehicle_efficiency")
        rows = []
        for _, row in eff_df.iterrows():
            rows.append((
                int(row["VehicleNum"]),
                int(row["trip_count"]),
                float(row.get("total_duration", 0)),
                float(row.get("total_distance", 0)),
                float(row.get("avg_duration", 0)),
                float(row.get("avg_distance", 0)),
                str(row.get("first_trip", "")),
                str(row.get("last_trip", "")),
            ))

        cursor.executemany(
            """INSERT INTO vehicle_efficiency
               (VehicleNum, trip_count, total_duration, total_distance,
                avg_duration, avg_distance, first_trip, last_trip)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            rows
        )
        conn.commit()
        cursor.close()
        self.log.info(f"车辆效率上传完成: {len(rows)} 条")

    def upload_net_flow(self, flow_df: pd.DataFrame):
        """上传净流入流出分析"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("TRUNCATE TABLE net_flow")
        active = flow_df[(flow_df["inflow"] > 0) | (flow_df["outflow"] > 0)]
        rows = []
        for _, row in active.iterrows():
            rows.append((
                int(row["grid_id"]),
                float(row["lng"]),
                float(row["lat"]),
                int(row["outflow"]),
                int(row["inflow"]),
                int(row["net_flow"]),
            ))

        cursor.executemany(
            """INSERT INTO net_flow
               (grid_id, lng, lat, outflow, inflow, net_flow)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            rows
        )
        conn.commit()
        cursor.close()
        self.log.info(f"净流量分析上传完成: {len(rows)} 条")

    def upload_realtime_cache(self, hourly_df=None, period_df=None,
                              hotspots_df=None, kpis=None):
        """上传实时统计缓存 (供 Web 实时大屏使用)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("TRUNCATE TABLE realtime_stats")
        rows = []

        if hourly_df is not None:
            trend_data = {
                "hours": [f"{h:02d}:00" for h in hourly_df["hour"]],
                "values": [int(v) for v in hourly_df["trip_count"].tolist()],
            }
            rows.append(("trend_data", "hourly", None,
                        json.dumps(trend_data, ensure_ascii=False)))

        if period_df is not None:
            for _, row in period_df.iterrows():
                rows.append(("period_trips", str(row["时段"]),
                           int(row["出行量"]), None))

        if hotspots_df is not None:
            ranking = []
            for _, row in hotspots_df.head(15).iterrows():
                ranking.append({
                    "name": f"#{int(row['cluster_id'])}",
                    "lng": float(row["center_lng"]),
                    "lat": float(row["center_lat"]),
                    "value": int(row["count"]),
                })
            rows.append(("hotspot_ranking", "top15", None,
                        json.dumps(ranking, ensure_ascii=False)))

        if hotspots_df is not None:
            heatmap = []
            for _, row in hotspots_df.iterrows():
                heatmap.append([
                    float(row["center_lat"]),
                    float(row["center_lng"]),
                    float(row["count"]),
                ])
            rows.append(("heatmap_data", "all", None,
                        json.dumps(heatmap, ensure_ascii=False)))

        if kpis is not None:
            rows.append(("kpi_summary", "all", None,
                        json.dumps(kpis, ensure_ascii=False)))

        if rows:
            cursor.executemany(
                """INSERT INTO realtime_stats (stat_type, stat_key, stat_value, extra_info)
                   VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE stat_value=VALUES(stat_value),
                   extra_info=VALUES(extra_info)""",
                rows
            )
            conn.commit()

        cursor.close()
        self.log.info(f"实时缓存上传完成: {len(rows)} 条")

    # ----------------------------------------------------------
    # 一键上传
    # ----------------------------------------------------------

    def upload_all(self, cleaned_df=None, hourly_df=None, period_df=None,
                   hotspots_df=None, efficiency_df=None, flow_df=None,
                   kpis=None):
        """
        一键上传所有分析结果到 MySQL

        流程: 确保表结构正确 → 逐表 TRUNCATE + INSERT
        """
        log = self.log
        log.section("上传分析结果到 MySQL (192.168.116.128:3306)")
        start = time.time()

        try:
            # 1. 确保表结构正确 (自动修复 schema 不匹配)
            self.ensure_tables()

            # 2. 逐个上传
            if cleaned_df is not None and len(cleaned_df) > 0:
                self.upload_od_trips(cleaned_df)

            if hourly_df is not None and len(hourly_df) > 0:
                self.upload_hourly_stats(hourly_df)

            if period_df is not None and len(period_df) > 0:
                self.upload_period_stats(period_df)

            if hotspots_df is not None and len(hotspots_df) > 0:
                self.upload_hotspots(hotspots_df)

            if efficiency_df is not None and len(efficiency_df) > 0:
                self.upload_vehicle_efficiency(efficiency_df)

            if flow_df is not None and len(flow_df) > 0:
                self.upload_net_flow(flow_df)

            # 3. 更新实时缓存
            self.upload_realtime_cache(hourly_df, period_df, hotspots_df, kpis)

            elapsed = time.time() - start
            log.info(f"[OK] 所有数据上传完成! 耗时: {elapsed:.2f}秒")

        except Exception as e:
            log.error(f"MySQL 上传失败: {e}")
            log.error(traceback.format_exc())
            raise
        finally:
            self.close()
