/**
 * 看板主入口
 * 渐进加载所有图表：并行 fetch 数据，每个数据到达立即渲染对应图表
 */
(function() {
    'use strict';

    var API = window.API;
    var CM = window.ChartManager;

    // ----------------------------------------------------------
    // KPI 卡片渲染
    // ----------------------------------------------------------
    function renderKPIs(kpis) {
        var container = document.getElementById('kpi-cards');
        if (!container || !kpis) return;
        container.innerHTML = kpis.map(function(k) {
            return '<div class="kpi-card">' +
                   '<div class="kpi-value">' + k.value + '</div>' +
                   '<div class="kpi-label">' + k.label + '</div>' +
                   '</div>';
        }).join('');
    }

    function renderKPIError() {
        var container = document.getElementById('kpi-cards');
        if (container) {
            container.innerHTML = '<div class="error-state">KPI 数据加载失败</div>';
        }
    }

    // ----------------------------------------------------------
    // 图表渲染 + 错误处理辅助
    // ----------------------------------------------------------
    function renderChart(chartModule, domId, data, name) {
        try {
            if (data) {
                chartModule.render(domId, data);
            } else {
                showError(domId, name);
            }
        } catch (e) {
            console.error('[Dashboard] 渲染 ' + name + ' 失败:', e);
            showError(domId, name);
        }
    }

    function showError(domId, name) {
        var dom = document.getElementById(domId);
        if (dom) {
            dom.innerHTML = '<div class="error-state">' + (name || '图表') + ' 数据加载失败</div>';
        }
    }

    // ----------------------------------------------------------
    // 并行加载所有数据，渐进渲染
    // ----------------------------------------------------------
    function boot() {
        // --- KPI 最先渲染 ---
        API.get('/api/kpis').then(function(data) {
            if (data) {
                renderKPIs(data);
            } else {
                renderKPIError();
            }
        });

        // --- 4 个原有图表 ---
        API.get('/api/hourly').then(function(d) {
            renderChart(window.HourlyChart, 'chart-hourly', d, '24h出行量');
        });
        API.get('/api/duration').then(function(d) {
            renderChart(window.DurationChart, 'chart-duration', d, '时长分布');
        });
        API.get('/api/period').then(function(d) {
            renderChart(window.PeriodChart, 'chart-period', d, '时段对比');
        });
        API.get('/api/hotspots').then(function(d) {
            renderChart(window.HotspotsChart, 'chart-hotspots', d, '热点区域');
        });

        // --- 5 个新图表 ---
        API.get('/api/distance').then(function(d) {
            renderChart(window.DistanceChart, 'chart-distance', d, '距离分布');
        });
        API.get('/api/speed').then(function(d) {
            renderChart(window.SpeedChart, 'chart-speed', d, '速度分布');
        });
        API.get('/api/vehicles').then(function(d) {
            renderChart(window.EfficiencyChart, 'chart-efficiency', d, '车辆效率');
        });
        API.get('/api/net-flow').then(function(d) {
            renderChart(window.NetFlowChart, 'chart-netflow', d, '净流入/流出');
        });
        API.get('/api/od-flows').then(function(d) {
            renderChart(window.ODSankeyChart, 'chart-sankey', d, 'OD流向');
        });
    }

    // ----------------------------------------------------------
    // 启动
    // ----------------------------------------------------------
    window.addEventListener('DOMContentLoaded', function() {
        boot();
    });

    // 窗口大小变化时自适应所有图表
    window.addEventListener('resize', function() {
        CM.resizeAll();
    });

})();
