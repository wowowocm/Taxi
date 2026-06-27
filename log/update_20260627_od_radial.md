# OD 流向图 + 放射状流向图 实施日志 — 2026-06-27

## 背景

用户要求将桑基图替换为 **OD 流向图**（坐标平面上的带箭头流向线）和 **放射状流向图**（圆形布局的流向网络图）。

## 改动概览

| 层级 | 文件 | 操作 |
|------|------|------|
| API | `src/web_app.py` | 重写 `_get_od_flow_data()`，移除 Sankey DAG 去环，返回带经纬度坐标的 nodes |
| JS | `src/static/js/charts/od-lines.js` | 🆕 **新增** — ECharts `lines` 系列 OD 流向图 |
| JS | `src/static/js/charts/od-radial.js` | 🆕 **新增** — ECharts `graph` 圆形布局放射状流向图 |
| JS | `src/static/js/charts/od-sankey.js` | ⚠️ 保留但不再引用（已从模板中移除） |
| HTML | `src/templates/index.html` | 桑基图卡片 → OD 流向图 + 放射状流向图两张全宽卡片 |
| JS | `src/static/js/dashboard.js` | ODSankeyChart → ODLinesChart + ODRadialChart |

---

## 一、API 改动

### `_get_od_flow_data()` — 重写

**返回格式**：
```json
{
  "nodes": [
    {"name": "(114.025,22.530)", "lng": 114.025, "lat": 22.530},
    ...
  ],
  "links": [
    {
      "source": 18, "target": 19,
      "source_name": "(114.115,22.530)", "target_name": "(114.115,22.540)",
      "value": 80
    },
    ...
  ]
}
```

- `nodes[].lng` / `nodes[].lat` — 经纬度浮点数，供 OD 流向图绘制坐标
- `links[].source` / `links[].target` — 数字索引，供放射状图 graph 系列使用
- `links[].source_name` / `links[].target_name` — 字符串名，供 tooltip 显示
- **不再做 DAG 去环** — 双向流合并为净值后直接输出（lines 和 graph 系列天然支持任意方向）

---

## 二、OD 流向图 — `od-lines.js`

### 技术选型
ECharts `lines` 系列 + cartesian2d 坐标系

### 视觉设计
```
图层1: lines 系列（灰色流向线 + 红色箭头粒子动效）
├── 线宽 = 0.5~6.5px（按流量比例映射）
├── 透明度 = 0.15~0.7
├── effect.period = 4s（粒子流动周期）
├── effect.symbol = 'arrow'（箭头粒子）
└── effect.symbolSize = 6

图层2: scatter 系列（网格节点散点）
├── 节点大小 = 4~20px（按节点总流量 sqrt 映射）
├── 标签 = 截断到 18 字符的节点名
└── 颜色 = #1a237e
```

### 交互
- tooltip: 悬停显示 O→D 方向 + 流量值
- emphasis: 高亮线宽 3px
- xAxis/yAxis: 显示经纬度坐标

---

## 三、放射状流向图 — `od-radial.js`

### 技术选型
ECharts `graph` 系列 + `layout: 'circular'`

### 视觉设计
```
series: graph
├── layout: 'circular'      # 圆形节点布局
├── circular.rotateLabel: true
├── edgeSymbol: ['none', 'arrow']  # 边上显示箭头标方向
├── categories: 高流量/中流量/低流量（三档颜色）
├── 节点大小 = 8~36px（按关联流量比例映射）
├── 边宽度 = 0.5~6.5px
├── 边透明度 = 0.2~0.8
├── 边曲率 = 0.15~0.35
└── roam: true, draggable: true    # 可拖拽/缩放
```

### 交互
- tooltip: 悬停节点显示关联流量，悬停边显示流向详情
- emphasis.focus: 'adjacency'（高亮邻接节点和边）
- legend: 三档流量分类图例
- 支持拖拽和缩放

---

## 四、依赖

无需额外导入。两个图表均使用页面已加载的 ECharts 5.5 + shine 主题。

---

## 五、验证结果（Puppeteer 无头浏览器）

```
=== All Charts Status ===
  [OK] 📈 24小时出行量分布 (chart-hourly)
  [OK] ⏱ 行程时长分布 (chart-duration)
  [OK] 🕐 各时段出行量对比 (chart-period)
  [OK] 📍 Top-15 出行热点区域 (chart-hotspots)
  [OK] 📏 行程距离分布 (chart-distance)
  [OK] ⚡ 行程速度分布 (chart-speed)
  [OK] 🚖 车辆运营效率 Top-15 (chart-efficiency)
  [OK] 🔄 区域净流入/流出 Top-30 (chart-netflow)
  [OK] 🌐 OD出行流向图（Top-30 OD对） (chart-odlines)
  [OK] 🕸 放射状出行流向图 (chart-radial)

=== OD Lines Chart ===
  hasCanvas: true, hasError: false ✅

=== Radial Chart ===
  hasCanvas: true, hasError: false ✅

Console Errors: (none except favicon.ico 404)
Console Warnings: (none)
```

- ✅ 10 张图表全部正常渲染
- ✅ OD 流向图 — 坐标平面上箭头粒子流动效果
- ✅ 放射状流向图 — 圆形节点布局 + 弧线
- ✅ `/api/od-flows` — 29 nodes（含 lng/lat）+ 25 links（合并双向流）
- ✅ 零 JS 异常
