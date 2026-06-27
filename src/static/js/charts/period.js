/**
 * 各时段出行量对比 — 柱状图
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Period] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: '3%', right: '4%', bottom: '5%', top: '10%', containLabel: true },
            xAxis: {
                type: 'category',
                data: data.labels
            },
            yAxis: {
                type: 'value',
                name: '占比 (%)',
                max: 100
            },
            series: [{
                name: '占比',
                data: data.values,
                type: 'bar',
                label: {
                    show: true,
                    position: 'top',
                    formatter: '{c}%',
                    fontSize: 13,
                    fontWeight: 'bold'
                }
            }]
        });
    }

    window.PeriodChart = { render: render };
})();
