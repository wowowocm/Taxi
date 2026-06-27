/**
 * 24小时出行量分布 — 折线图
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Hourly] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true },
            xAxis: {
                type: 'category',
                data: data.hours,
                name: '小时',
                nameLocation: 'center',
                nameGap: 30
            },
            yAxis: {
                type: 'value',
                name: '出行量 (次)'
            },
            series: [{
                name: '出行量',
                data: data.values,
                type: 'line',
                smooth: true,
                areaStyle: { opacity: 0.15 },
                markLine: {
                    silent: true,
                    data: [{ type: 'average', name: '均值' }],
                    lineStyle: { type: 'dashed' }
                }
            }]
        });
    }

    window.HourlyChart = { render: render };
})();
