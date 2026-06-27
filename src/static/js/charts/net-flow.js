/**
 * 区域净流入/流出 — 发散柱状图
 * 数据源: /api/net-flow
 */
(function() {
    'use strict';

    function render(domId, data) {
        if (!data) { console.warn('[NetFlow] 无数据'); return; }
        var inst = window.ChartManager.init(domId);
        if (!inst) return;

        var allLabels = data.out_labels.concat(data.in_labels.reverse());
        var allValues = [];

        // 负值 = 净流出（左），正值 = 净流入（右）
        data.out_values.forEach(function(v) {
            allValues.push(-v);  // 流出 → 负值（左柱）
        });
        data.in_values.reverse().forEach(function(v) {
            allValues.push(v);   // 流入 → 正值（右柱）
        });

        inst.setOption({
            tooltip: {
                trigger: 'axis',
                formatter: function(params) {
                    var val = params[0].value;
                    var absVal = Math.abs(val);
                    var dir = val >= 0 ? '净流入' : '净流出';
                    return params[0].name + '<br/>' + dir + ': <b>' + absVal + '</b> 次';
                }
            },
            grid: { left: '28%', right: '4%', bottom: '5%', top: '5%' },
            xAxis: {
                type: 'value',
                name: '净流量 (次)',
                axisLabel: {
                    formatter: function(v) { return Math.abs(v); }
                }
            },
            yAxis: {
                type: 'category',
                data: allLabels,
                axisLabel: { fontSize: 10 }
            },
            series: [{
                name: '净流量',
                data: allValues,
                type: 'bar',
                label: {
                    show: true,
                    position: 'right',
                    fontSize: 10,
                    formatter: function(p) {
                        return Math.abs(p.value);
                    }
                },
                itemStyle: {
                    color: function(params) {
                        return params.value >= 0 ? '#2b821d' : '#c12e34';
                    }
                }
            }]
        });
    }

    window.NetFlowChart = { render: render };
})();
