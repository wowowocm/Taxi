/**
 * Top-15 出行热点区域 — 水平柱状图
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Hotspots] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: '28%', right: '4%', bottom: '5%', top: '5%' },
            xAxis: {
                type: 'value',
                name: '出行量 (次)'
            },
            yAxis: {
                type: 'category',
                data: data.labels,
                inverse: true,
                axisLabel: { fontSize: 10 }
            },
            series: [{
                name: '出行量',
                data: data.values,
                type: 'bar',
                label: {
                    show: true,
                    position: 'right',
                    fontSize: 10,
                    formatter: function(p) {
                        return p.value.toLocaleString() + '次';
                    }
                }
            }]
        });
    }

    window.HotspotsChart = { render: render };
})();
