/**
 * 行程距离分布 — 柱状图 + 统计副标题
 * 数据源: /api/distance
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Distance] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            title: {
                subtext: '短途(<3km): ' + (data.short_ratio || 0).toFixed(1) +
                         '% | 长途(>10km): ' + (data.long_ratio || 0).toFixed(1) +
                         '% | 均值: ' + (data.mean || 0).toFixed(1) + 'km',
                subtextStyle: { fontSize: 12, color: '#666' },
                left: 'center',
                top: 5
            },
            tooltip: {
                trigger: 'axis',
                formatter: function(p) {
                    return p[0].name + '<br/>行程数: <b>' +
                           p[0].value.toLocaleString() + '</b> 次';
                }
            },
            grid: { left: '3%', right: '4%', bottom: '12%', top: '18%', containLabel: true },
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
                    fontSize: 10,
                    formatter: function(p) {
                        return p.value > 0 ? p.value.toLocaleString() : '';
                    }
                },
                markLine: {
                    silent: true,
                    data: [
                        { yAxis: 3, name: '3km 分界线', lineStyle: { type: 'dashed', color: '#e6b600' } }
                    ]
                }
            }]
        });
    }

    window.DistanceChart = { render: render };
})();
