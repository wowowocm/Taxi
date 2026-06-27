# Flask 启动修复 + OD 桑基图修复日志 — 2026-06-27

## 问题一：`python main.py --web` 无法启动 Flask 服务器

### 根因

系统默认 `python` 为 Python 3.12.4，使用的是 `.venv` 虚拟环境（该环境中**未安装 Flask**）。
而项目实际依赖安装在 `.venv_py38`（Python 3.8.10）环境中。

### 修复

在 `main.py` 中添加虚拟环境自动检测与转发机制：
- `_find_venv_python()` — 扫描 `.venv_py38` 和 `.venv`
- `_relaunch_with_venv()` — 检查 Flask 可用性，自动切换 venv
- `run_web()` — 入口处先 `import flask`，失败则自动转发

### 改动文件

`main.py`

---

## 问题二：OD 流向桑基图"数据加载失败"（两个子问题）

### 子问题 A：`layout: 'none'` 导致节点锁定在原点

**根因**：`od-sankey.js` 中设置 `layout: 'none'`，要求手动提供 x/y 坐标。
后端只返回节点名，未提供坐标 → 所有节点堆叠在 (0,0) → 图表空白。

**修复**（第一轮）：移除 `layout: 'none'`，添加 `nodeAlign: 'left'`，改进错误处理。

### 子问题 B：数据中存在循环 → ECharts 抛异常 ★ 真正根因

**错误信息**（来自 Puppeteer 无头浏览器）：
```
[Dashboard] 渲染 OD流向 失败: Error: Sankey is a DAG, the original data has cycle!
```

**分析**：ECharts Sankey 要求输入为 **DAG（有向无环图）**。
30 条原始 OD 链接中存在 **5 对双向流**（互为反向），构成循环：

| 双向流 | 正向值 | 反向值 | 净值 |
|--------|--------|--------|------|
| `(114.045,22.540) ⇄ (114.045,22.530)` | 19 | 15 | 4→ |
| `(114.085,22.540) ⇄ (114.075,22.540)` | 15 | 11 | 4→ |
| `(114.115,22.548) ⇄ (114.115,22.540)` | 15 | 11 | 4→ |
| `(114.095,22.540) ⇄ (114.085,22.540)` | 12 | 11 | 1→ |
| `(114.125,22.548) ⇄ (114.125,22.540)` | 12 | 10 | 2→ |

**修复**（第二轮）：

在 `web_app.py` 的 `_get_od_flow_data()` 中添加两阶段循环消除：

1. **步骤1 — 合并双向流**：对于 A→B 和 B→A，保留净值中主导方向，丢弃反向
2. **步骤2 — Kahn 拓扑排序**：利用拓扑排序检测更长循环（≥3 节点），迭代移除最小流边直至 DAG

同时更新 `od-sankey.js`：
- `inst.setOption()` 包裹 try-catch，捕获 ECharts 异常并显示具体错误信息
- 避免因未被拦截的异常导致白屏

### 改动文件

| 文件 | 改动 |
|------|------|
| `src/web_app.py` | `_get_od_flow_data()` 添加双向流合并 + Kahn 去环算法 |
| `src/static/js/charts/od-sankey.js` | 移除 `layout: 'none'`、`nodeAlign: 'left'`、`setOption` try-catch |
| `main.py` | 添加 venv 自动检测与转发 |

### 验证结果（Puppeteer 无头浏览器）

```
=== 所有图表状态 ===
  [OK] 📈 24小时出行量分布 (chart-hourly)
  [OK] ⏱ 行程时长分布 (chart-duration)
  [OK] 🕐 各时段出行量对比 (chart-period)
  [OK] 📍 Top-15 出行热点区域 (chart-hotspots)
  [OK] 📏 行程距离分布 (chart-distance)
  [OK] ⚡ 行程速度分布 (chart-speed)
  [OK] 🚖 车辆运营效率 Top-15 (chart-efficiency)
  [OK] 🔄 区域净流入/流出 Top-30 (chart-netflow)
  [OK] 🌐 OD出行流向桑基图（Top-30 OD对） (chart-sankey)

=== Sankey DOM 状态 ===
  hasError: false
  hasCanvas: true
  hasInstance: true
```

- ✅ 9 张图表全部正常渲染
- ✅ `/api/od-flows` → 29 nodes + 25 links（5 对双向流合并为净值）
- ✅ 零双向循环残留
- ✅ ECharts 自动布局 + `nodeAlign: 'left'` 正常工作
- ✅ 无 JS 异常
