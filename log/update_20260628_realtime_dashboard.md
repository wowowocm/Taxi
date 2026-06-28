# 深圳出租车实时运行态势大屏 — 更新日志 2026-06-28

## 目标

根据 `final_result/实现文本.md` 的技术方案和 `final_result/f5e34becda454c81974ccfc9574fd8da.png` 参考图，实现**暗黑科幻风格实时大数据可视化大屏**，数据源切换为 **MySQL 数据库**。

## 技术架构

```
数据源: MySQL 8.0 (192.168.116.128) ← CSV导入
    ↓
后端: Python Flask + PyMySQL (实时API)
    ↓
前端: HTML/CSS/JS + Leaflet地图 + ECharts图表
    ↓
大屏: 暗黑科幻风格 全屏实时看板
```

## 改动文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/web_app.py` | ✏️ 新增 | 添加 8 个实时大屏 API 路由 (`/realtime`, `/api/realtime/*`)，MySQL 数据源 |
| `src/templates/realtime.html` | ✚ 新建 | 全屏实时大屏 HTML 模板（三栏布局） |
| `src/static/css/realtime.css` | ✚ 新建 | 暗黑科幻风格 CSS（深蓝背景、发光边框、渐变文字） |
| `src/static/js/realtime.js` | ✚ 新建 | 前端 JS 逻辑（Leaflet 热力图 + ECharts 趋势图 + 排行榜 + KPI） |

## 数据库 (MySQL)

### 连接信息
- **Host**: 192.168.116.128:3306
- **User**: root
- **Database**: taxi_analysis
- **Charset**: utf8mb4

### 数据表

| 表名 | 行数 | 说明 |
|------|------|------|
| `gps_trajectory` | 99,837 | GPS 轨迹采样数据（前10万条） |
| `od_trips` | 8,517 | OD 行程数据（完整导入） |
| `realtime_stats` | 45 | 预计算聚合统计缓存（KPI/排行/趋势/热力图/时段） |

### 聚合缓存内容

| stat_type | 数量 | 说明 |
|-----------|------|------|
| `kpi_summary` | 1 | 总出行量、活跃车辆、平均时长/距离/速度 |
| `hourly_trips` | 24 | 24小时出行量分布 |
| `hotspot_ranking` | 15 | Top-15 上车热点排行 |
| `period_trips` | 4 | 早高峰/日间平峰/晚高峰/夜间 对比 |
| `trend_data` | 24 | 24小时出行量+平均速度+平均距离趋势 |
| `heatmap_data` | 500 | 热力图坐标点（网格聚合 Top-500） |

## 新增 API 端点（8个）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/realtime` | GET | 实时运行态势大屏页面 |
| `/api/realtime/kpis` | GET | KPI 指标（总出行量/活跃车辆/平均时长/距离/速度） |
| `/api/realtime/heatmap` | GET | 热力图数据（500个坐标点+权重） |
| `/api/realtime/ranking` | GET | Top-15 上车热点排行 |
| `/api/realtime/trend` | GET | 24小时趋势数据（出行量+速度的双Y轴数据） |
| `/api/realtime/period` | GET | 4时段出行量对比 |
| `/api/realtime/hourly` | GET | 24小时出行量分布 |
| `/api/realtime/dashboard` | GET | 聚合所有实时数据（单次请求获取全部） |

## 前端大屏布局

```
┌──────────────────────────────────────────────────┐
│            🚕 深圳市出租车实时运行态势              │  ← 标题栏
├──────────┬────────┬──────────┬──────────┬─────────┤
│ 📊 总出行量 │ 🚖 活跃车辆│ ⏱ 平均时长 │ 📏 平均距离 │ ⚡ 平均速度 │  ← KPI 卡片行
├──────────┼────────┴──────────┼──────────┤
│          │                  │ 📈 24h出行量&速度 │  ← 右侧上
│ 🏆 热点  │   🗺 深圳地图     │   (双Y轴趋势图)   │
│   排行   │   Leaflet 深色底图 │                  │
│  (列表)  │   + 热力图叠加    ├──────────────────┤
│          │                  │ 🕐 各时段出行量   │  ← 右侧下
│          │                  │   (柱状对比图)    │
├──────────┴──────────────────┴──────────────────┤
│  数据源: MySQL @ 192.168.116.128  │  🕐 时钟  │  版权  │  ← 底部信息条
└──────────────────────────────────────────────────┘
```

## 关键特性

- **暗黑科幻主题** — 深蓝渐变背景 + 发光边框 + 渐变色文字 + 荧光配色
- **Leaflet 地图** — CartoDB 深色瓦片（免 API Key）+ 热力图渐变（蓝→青→绿→黄→橙→红）
- **双 Y 轴趋势图** — ECharts dark 主题，出行量（青蓝色面积图，左Y轴）+ 平均速度（橙色折线，右Y轴）
- **热点排行联动** — 点击左侧排行项，地图自动 flyTo 到对应坐标位置
- **30秒自动刷新** — 数据轮询更新，时钟每秒刷新
- **响应式** — 三栏 Flex 布局 + resize 事件处理
- **MySQL 数据源** — 所有 API 从 MySQL `realtime_stats` 缓存表读取，毫秒级响应

## 前端依赖 (CDN)

| 库 | 版本 | 用途 |
|----|------|------|
| ECharts | 5.5.0 | 趋势图 + 时段对比图 |
| Leaflet | 1.9.4 | 地图底图 |
| Leaflet.Heat | 0.2.0 | 热力图叠加层 |

## 数据 KPI 摘要

| 指标 | 值 |
|------|-----|
| 总出行量 | 8,517 次 |
| 活跃车辆 | 353 辆 |
| 平均行程时长 | 11.9 分钟 |
| 平均行程距离 | 2.46 km |
| 平均速度 | 13.1 km/h |
| 高峰小时 | 22:00 (542次) |
| 最大热点 | (114.08, 22.55) — 137次 |

## 启动方式

```bash
# Windows (使用项目虚拟环境)
.venv_py38\Scripts\activate
python main.py --web

# 访问地址
# 原始看板:  http://localhost:5000/
# 实时大屏:  http://localhost:5000/realtime
```

## 注意事项

1. **MySQL 必须可达** — 确保 192.168.116.128 的 MySQL 服务正常运行
2. **网络依赖** — 前端 Leaflet/ECharts 通过 CDN 加载，需要互联网连接
3. **地图底图** — 使用免费 CartoDB 深色瓦片，如需高德地图请替换并配置 API Key
4. **数据更新** — 当前为静态 CSV 导入数据，生产环境建议改用 Kafka/Redis 实时数据管道

## 验证结果

```
Flask Test Client 验证:
  [OK] /realtime — HTTP 200 (5,431 bytes)
  [OK] /api/realtime/kpis — 返回5项KPI数据
  [OK] /api/realtime/heatmap — 返回500个热力坐标点
  [OK] /api/realtime/ranking — 返回15个热点排行
  [OK] /api/realtime/trend — 返回24小时双指标趋势
  [OK] /api/realtime/period — 返回4时段对比数据
  [OK] /api/realtime/dashboard — 聚合6类数据正常

静态文件:
  [OK] /static/css/realtime.css — 9,995 bytes
  [OK] /static/js/realtime.js — 14,713 bytes
  [OK] /static/js/core/api.js — 1,483 bytes
  [OK] /static/js/core/chart-manager.js — 912 bytes

MySQL:
  [OK] gps_trajectory: 99,837 条
  [OK] od_trips: 8,517 条
  [OK] realtime_stats: 45 条聚合缓存
```
