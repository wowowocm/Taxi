/**
 * 行程速度分布 — 直方图
 * 数据源: /api/speed
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Speed] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            title: {
                subtext: '均值: ' + (data.mean || 0).toFixed(1) +
                         ' km/h | 中位数: ' + (data.median || 0).toFixed(1) + ' km/h',
                subtextStyle: { fontSize: 12, color: '#666' },
                left: 'center',
                top: 5
            },
            tooltip: {
                trigger: 'axis',
                formatter: function(p) {
                    var val = p[0].value;
                    var total = data.total || 1;
                    var pct = (val / total * 100).toFixed(1);
                    return p[0].name + '<br/>行程数: <b>' +
                           val.toLocaleString() + '</b> 次 (' + pct + '%)';
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
                    data: [{ xAxis: data.mean_idx || 0, name: '均值', lineStyle: { type: 'dashed' } }]
                }
            }]
        });
    }

    window.SpeedChart = { render: render };
})();
