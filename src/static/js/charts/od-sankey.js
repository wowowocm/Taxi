/**
 * OD出行流向 — 桑基图
 * 数据源: /api/od-flows
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Sankey] 无数据'); return; }
        if (!data.nodes || !data.links || data.links.length === 0) {
            console.warn('[Sankey] 无流向数据');
            return;
        }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            tooltip: {
                trigger: 'item',
                triggerOn: 'mousemove',
                formatter: function(p) {
                    if (p.dataType === 'edge') {
                        return p.data.source + ' → ' + p.data.target +
                               '<br/>流量: <b>' + p.data.value + '</b> 次';
                    }
                    return p.name + '<br/>合计: <b>' + (p.value || 0).toLocaleString() + '</b> 次';
                }
            },
            series: [{
                type: 'sankey',
                layout: 'none',
                layoutIterations: 32,
                emphasis: {
                    focus: 'adjacency',
                    lineStyle: { opacity: 0.8 }
                },
                data: data.nodes,
                links: data.links,
                label: {
                    fontSize: 10,
                    formatter: function(p) {
                        // 截断过长标签
                        return p.name.length > 18 ? p.name.substring(0, 16) + '…' : p.name;
                    }
                },
                lineStyle: {
                    color: 'gradient',
                    curveness: 0.5
                },
                nodeWidth: 18,
                nodeGap: 12
            }]
        });
    }

    window.ODSankeyChart = { render: render };
})();
