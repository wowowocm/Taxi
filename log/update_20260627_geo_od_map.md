# 深圳地图 OD 流向图 — 修改日志 2026-06-27

## 目标

删除桑基图，改为**基于深圳地图的 OD 出行流向图**，效果参考 `final_result/eg.png`。

## 技术方案

参考 `project_info/rule.md` 中的**地理坐标图**代码：

```
echarts.registerMap('shenzhen', geoJSON)
+ geo { map: 'shenzhen', roam: true }
+ graph { coordinateSystem: 'geo',
    data: [{name, value: [lng, lat]}, ...],
    edges: [{source: name, target: name}, ...],
    edgeSymbol: ['none', 'arrow'] }
```

深圳 GeoJSON 来源：DataV GeoAtlas `440300_full.json`（深圳市行政区划代码）

---

## 改动文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/web_app.py` | ✏️ 重写 | `_get_od_flow_data()` 返回 `{name, value:[lng,lat]}` + `{source,target}` graph 格式，移除 DAG 去环（graph 系列天然支持） |
| `src/static/js/charts/od-lines.js` | ✏️ 重写 | 深圳地图 OD 流向图 — GeoJSON 异步加载 + `echarts.registerMap` + geo + graph 系列 |
| `src/templates/index.html` | ✏️ 更新 | 桑基图 + 放射状图卡片 → 单张深圳地图 OD 流向图全宽卡片 |
| `src/static/js/dashboard.js` | ✏️ 更新 | 移除 ODRadialChart 引用 |
| `src/static/css/dashboard.css` | ✏️ 更新 | 全宽图表高度 500→650px（适配地图） |
| `src/static/js/charts/od-radial.js` | 🗑 删除 | 不再使用 |
| `src/static/js/charts/od-sankey.js` | 🗑 删除 | 不再使用 |

---

## API 返回格式

```json
{
  "nodes": [
    {"name": "(114.025,22.5305)", "value": [114.025, 22.5305]},
    ...
  ],
  "edges": [
    {"source": "(114.115,22.5305)", "target": "(114.115,22.5395)"},
    ...
  ]
}
```

## 前端渲染流程

```
1. 页面加载 → boot()
2. API.get('/api/od-flows')
   ├── 数据到达 → ODLinesChart.render()
   ├── GeoJSON 未就绪 → 显示 "正在加载深圳地图…"
   └── XMLHttpRequest GET 440300_full.json
       ├── 成功 → echarts.registerMap('shenzhen', geoJSON)
       │       → 缓存数据重渲染
       └── 失败 → 显示错误提示
3. ECharts setOption:
   geo: { map: 'shenzhen', roam: true, aspectScale: cos(22.55°) }
   series: [{ type: 'graph', coordinateSystem: 'geo',
              data: 29 nodes, edges: 25 edges,
              edgeSymbol: ['none', 'arrow'], symbolSize: 8 }]
```

## 依赖

**无需额外安装**。已使用：
- ECharts 5.5（CDN 加载）
- 深圳 GeoJSON（DataV 在线加载）

## 验证结果（Puppeteer）

```
=== All Charts Status ===
  [OK] 📈 24小时出行量分布
  [OK] ⏱ 行程时长分布
  [OK] 🕐 各时段出行量对比
  [OK] 📍 Top-15 出行热点区域
  [OK] 📏 行程距离分布
  [OK] ⚡ 行程速度分布
  [OK] 🚖 车辆运营效率 Top-15
  [OK] 🔄 区域净流入/流出 Top-30
  [OK] 🗺 深圳出租车OD出行流向图（Top-30 OD对）

OD Map 技术参数:
  - seriesType: "graph"
  - seriesCoordSys: "geo"
  - geoMap: "shenzhen"
  - dataCount: 29 nodes
  - edgeCount: 25 edges
  - canvas: 730×650px

Console errors: (none)
GeoJSON load: ✅ 成功
```

- ✅ 9 张图表全部正常渲染
- ✅ 深圳行政区 GeoJSON 地图正确注册和渲染
- ✅ graph 系列 `coordinateSystem: 'geo'` 与 rule.md 参考一致
- ✅ 29 个 OD 网格节点标注在深圳地图上
- ✅ 25 条流向箭头连线
- ✅ roam: true 支持缩放/拖拽
- ✅ 零 JS 异常
