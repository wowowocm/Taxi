/**
 * 行程时长分布 — 柱状图
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Duration] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            tooltip: {
                trigger: 'axis',
                formatter: function(p) {
                    return p[0].name + '<br/>出行量: <b>' +
                           p[0].value.toLocaleString() + '</b> 次';
                }
            },
            grid: { left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true },
            xAxis: {
                type: 'category',
                data: data.labels,
                axisLabel: { rotate: 30, fontSize: 11 }
            },
            yAxis: {
                type: 'value',
                name: '行程数 (次)'
            },
            series: [{
                name: '行程数',
                data: data.values,
                type: 'bar',
                label: {
                    show: true,
                    position: 'top',
                    rotate: 45,
                    fontSize: 10
                }
            }]
        });
    }

    window.DurationChart = { render: render };
})();
