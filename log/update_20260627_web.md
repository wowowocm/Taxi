# Web 平台化更新日志 — 2026-06-27

## 一、架构重构

### 从单文件内联 → Jinja2 + 静态文件分离

**重构前:** `web_app.py` 包含 200+ 行 `DASHBOARD_HTML` Python 字符串，
所有 CSS/JS/HTML 混合在一起，难以维护。

**重构后:** 清晰的三层分离：

```
src/
├── web_app.py              # 薄路由层（10个API + 1个页面）
├── templates/
│   ├── base.html           # Jinja2 基模板（CSS/JS 链接、header、footer）
│   └── index.html          # 看板页面（9个图表卡片 + script 加载）
└── static/
    ├── css/dashboard.css   # 所有样式（含响应式、错误状态）
    └── js/
        ├── echarts/shine.js      # ECharts shine 主题
        ├── core/
        │   ├── api.js            # fetch 封装（window.API）
        │   └── chart-manager.js  # echarts.init(dom, 'shine') 统一管理
        ├── charts/
        │   ├── hourly.js         # 24h 折线图
        │   ├── duration.js       # 时长柱状图
        │   ├── period.js         # 时段对比图
        │   ├── hotspots.js       # 热点水平柱状图
        │   ├── distance.js       # [NEW] 距离分布
        │   ├── speed.js          # [NEW] 速度分布
        │   ├── efficiency.js     # [NEW] 车辆效率
        │   ├── net-flow.js       # [NEW] 净流入/流出
        │   └── od-sankey.js      # [NEW] OD 桑基图
        └── dashboard.js          # 主入口（渐进加载）
```

## 二、新增 API 端点（10个）

| 端点 | 说明 | 新增？ |
|------|------|--------|
| `/` | Jinja2 模板渲染页面 | 🆕 重构 |
| `/api/kpis` | 5个 KPI 卡片 | 🆕 拆分 |
| `/api/hourly` | 24小时出行量 | 🆕 拆分 |
| `/api/duration` | 时长分布（7段） | 🆕 拆分 |
| `/api/period` | 4时段占比 | 🆕 拆分 |
| `/api/hotspots` | Top-15 热点 | 🆕 拆分 |
| `/api/distance` | 距离分布（7段） | ✨ 新增 |
| `/api/speed` | 速度分布（8段） | ✨ 新增 |
| `/api/vehicles` | 车辆效率 Top-15 | ✨ 新增 |
| `/api/od-flows` | OD 桑基图数据 | ✨ 新增 |
| `/api/net-flow` | 净流入/流出 Top±15 | ✨ 新增 |
| `/api/dashboard` | 聚合端点（向后兼容） | 🔄 扩展 |
| `/api/health` | 健康检查 | 保留 |

## 三、新增可视化图表（5张）

| 图表 | 类型 | 数据源 | 亮点 |
|------|------|--------|------|
| 📏 行程距离分布 | Bar + stats subtitle | `distance_km` 自定义分箱 | 短途/长途占比标注 |
| ⚡ 行程速度分布 | Bar + mean markLine | `avg_speed` 自定义分箱 | 均值参考线 |
| 🚖 车辆运营效率 | Horizontal Bar | `vehicle_efficiency().head(15)` | 详细 tooltip |
| 🔄 区域净流入/流出 | Diverging Bar | `net_flow_analysis()` Top±15 | 红绿发散配色 |
| 🌐 OD流向桑基图 | Sankey | `top_od_pairs(30)` | 节点自适应布局 |

## 四、技术亮点

1. **shine 主题**: 所有图表通过 `ChartManager.init()` 统一应用，
   8 色调色板自动分配，不再手动指定颜色
2. **渐进加载**: 10 个 API 并行 fetch，每个数据到达立即渲染
3. **降级处理**: 任一 API 失败不影响其他图表
4. **响应式**: CSS Grid `auto-fit minmax(500px, 1fr)` + resize 监听
5. **扩展 `init_data()`**: 启动时预计算 OD 矩阵、热点、净流量，
   确保 API 秒级响应

## 五、测试结果

- ✅ URL 首页返回正确 HTML（Jinja2 渲染）
- ✅ `/api/kpis` 返回 5 项 KPI
- ✅ `/api/hourly` 返回 24 小时数据
- ✅ `/api/distance` 返回 7 段距离分布（均值 2.46km）
- ✅ `/api/speed` 返回 8 段速度分布（均值 13.1km/h）
- ✅ `/api/vehicles` 返回 Top-15 车辆
- ✅ `/api/od-flows` 返回 29 节点 + 30 条链接
- ✅ `/api/net-flow` 返回 15 流入 + 15 流出
- ✅ `/api/dashboard` 聚合端点向后兼容（10 个 key）
- ✅ 9 张图表卡片全部在 HTML 中确认
- ✅ shine.js 主题被正确加载
- ✅ 无 JS 报错，无 CJK 字体警告
