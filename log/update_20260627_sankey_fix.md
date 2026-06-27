# OD 桑基图修复日志 — 2026-06-27

## 问题

浏览器中 OD 流向桑基图显示"数据加载失败"。

## 根因

`src/static/js/charts/od-sankey.js` 第 31 行设置了 `layout: 'none'`。

ECharts Sankey 图表的 `layout` 属性控制节点布局算法:
- 默认（不设置）: ECharts 使用内置迭代布局算法自动计算节点位置
- `layout: 'none'`: 禁用自动布局，要求手动为每个节点提供 `x`/`y` 坐标

设置 `layout: 'none'` 后，29 个节点的默认位置全部锁定在原点 (0, 0)，所有节点重叠，
图表渲染为空白区域。

## 修复

### 改动文件

`src/static/js/charts/od-sankey.js`

### 改动内容

1. **移除 `layout: 'none'`** → 恢复 ECharts 自动布局算法
2. **添加 `nodeAlign: 'left'`** → OD 起点节点对齐到左侧，终点在右侧
3. **改进错误处理** → 无数据时直接显示 `<div class="error-state">` 而非静默返回
4. **增加 DOM 检查** → 防止 `ChartManager.init()` 在 DOM 不存在时返回 null

### 对比

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| layout | `'none'` (禁止自动布局) | 不设置 (默认迭代布局) |
| nodeAlign | 无 | `'left'` (O点左对齐) |
| 错误反馈 | 静默返回，用户看到空白 | 显示具体错误提示 |
| nodeWidth | 18 | 20 |
| nodeGap | 12 | 10 |

## 验证

- ✅ `/api/od-flows` 返回 29 个节点、30 条链接
- ✅ 节点名与链接 source/target 完全匹配（零孤儿）
- ✅ `layout: 'none'` 已移除
- ✅ 全部 JS 文件在 HTML 页面中正确加载
