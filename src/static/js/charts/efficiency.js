/**
 * 车辆运营效率 Top-15 — 水平柱状图
 * 数据源: /api/vehicles
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[Efficiency] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        inst.setOption({
            tooltip: {
                trigger: 'axis',
                formatter: function(params) {
                    var idx = params[0].dataIndex;
                    var v = data.vehicles[idx];
                    return '<b>车辆 #' + v.id + '</b><br/>' +
                           '载客次数: ' + v.trips + ' 次<br/>' +
                           '总时长: ' + (v.total_dur || 0).toFixed(0) + ' 分钟<br/>' +
                           '总距离: ' + (v.total_dist || 0).toFixed(1) + ' km<br/>' +
                           '均次时长: ' + (v.avg_dur || 0).toFixed(1) + ' 分钟<br/>' +
                           '均次距离: ' + (v.avg_dist || 0).toFixed(2) + ' km';
                }
            },
            grid: { left: '15%', right: '4%', bottom: '5%', top: '5%' },
            xAxis: {
                type: 'value',
                name: '载客次数'
            },
            yAxis: {
                type: 'category',
                data: data.vehicles.map(function(v) { return '# ' + v.id; }),
                inverse: true,
                axisLabel: { fontSize: 11 }
            },
            series: [{
                name: '载客次数',
                data: data.vehicles.map(function(v) { return v.trips; }),
                type: 'bar',
                label: {
                    show: true,
                    position: 'right',
                    fontSize: 10,
                    formatter: function(p) {
                        return p.value + '次';
                    }
                }
            }]
        });
    }

    window.EfficiencyChart = { render: render };
})();
