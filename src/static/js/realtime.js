/**
 * 深圳出租车实时运行态势 — 大屏 JS 逻辑
 *
 * 架构:
 *   1. Leaflet 地图 + 热力图 (中心区域)
 *   2. ECharts 趋势图 (右侧上方, 双Y轴)
 *   3. ECharts 时段对比图 (右侧下方)
 *   4. DOM 排行列表 (左侧)
 *   5. KPI 卡片 (顶部)
 *   6. 每 30 秒自动刷新数据
 */
(function() {
    'use strict';

    var API = window.API;

    // ================================================================
    // 全局状态
    // ================================================================
    var map = null;
    var heatLayer = null;
    var trendChart = null;
    var periodChart = null;
    var rankingData = [];
    var autoRefreshTimer = null;
    var REFRESH_INTERVAL = 30000; // 30秒刷新

    // 深圳中心坐标
    var SZ_CENTER = [22.55, 114.05];
    var SZ_ZOOM = 12;

    // ================================================================
    // 1. 地图初始化 (Leaflet + 深色瓦片 + 热力图)
    // ================================================================
    function initMap() {
        // 使用 CartoDB 深色底图（免费无需API Key）
        map = L.map('map-container', {
            center: SZ_CENTER,
            zoom: SZ_ZOOM,
            zoomControl: true,
            preferCanvas: true,
        });

        // 深色瓦片图层
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 18,
        }).addTo(map);

        // 热力图图层（初始空数据）
        heatLayer = L.heatLayer([], {
            radius: 18,
            blur: 12,
            maxZoom: 14,
            max: 50,
            gradient: {
                0.0: 'rgba(0, 0, 255, 0)',
                0.3: 'rgba(0, 255, 255, 0.5)',
                0.5: 'rgba(0, 255, 0, 0.6)',
                0.7: 'rgba(255, 255, 0, 0.7)',
                0.9: 'rgba(255, 140, 0, 0.8)',
                1.0: 'rgba(255, 0, 0, 0.9)',
            },
        }).addTo(map);

        console.log('[Realtime] 地图初始化完成 (Leaflet + CartoDB Dark)');
    }

    // ================================================================
    // 2. 趋势图初始化 (ECharts — 双Y轴)
    // ================================================================
    function initTrendChart() {
        var dom = document.getElementById('chart-trend');
        if (!dom) return;

        trendChart = echarts.init(dom, 'dark');
        var option = {
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(6, 14, 50, 0.9)',
                borderColor: 'rgba(0, 180, 255, 0.4)',
                textStyle: { color: '#e0f0ff', fontSize: 12 },
            },
            legend: {
                data: ['出行量(次)', '平均速度(km/h)'],
                top: 5,
                textStyle: { color: '#8ab4d6', fontSize: 11 },
            },
            grid: {
                left: 45, right: 55, top: 48, bottom: 30,
            },
            xAxis: {
                type: 'category',
                data: [],
                axisLine: { lineStyle: { color: 'rgba(0,150,220,0.3)' } },
                axisLabel: { color: '#8ab4d6', fontSize: 10, rotate: 45 },
            },
            yAxis: [
                {
                    type: 'value',
                    name: '出行量(次)',
                    nameTextStyle: { color: '#00d4ff', fontSize: 10 },
                    axisLine: { lineStyle: { color: '#00d4ff' } },
                    axisLabel: { color: '#00d4ff', fontSize: 10 },
                    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
                },
                {
                    type: 'value',
                    name: '速度(km/h)',
                    nameTextStyle: { color: '#ff8c42', fontSize: 10 },
                    axisLine: { lineStyle: { color: '#ff8c42' } },
                    axisLabel: { color: '#ff8c42', fontSize: 10 },
                    splitLine: { show: false },
                },
            ],
            series: [
                {
                    name: '出行量(次)',
                    type: 'line',
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 4,
                    data: [],
                    lineStyle: { color: '#00d4ff', width: 2 },
                    itemStyle: { color: '#00d4ff' },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
                            { offset: 1, color: 'rgba(0, 212, 255, 0.02)' },
                        ]),
                    },
                },
                {
                    name: '平均速度(km/h)',
                    type: 'line',
                    smooth: true,
                    symbol: 'diamond',
                    symbolSize: 4,
                    yAxisIndex: 1,
                    data: [],
                    lineStyle: { color: '#ff8c42', width: 2 },
                    itemStyle: { color: '#ff8c42' },
                },
            ],
        };
        trendChart.setOption(option);
        console.log('[Realtime] 趋势图初始化完成');
    }

    // ================================================================
    // 3. 时段对比图初始化 (ECharts — 柱状图)
    // ================================================================
    function initPeriodChart() {
        var dom = document.getElementById('chart-period');
        if (!dom) return;

        periodChart = echarts.init(dom, 'dark');
        var option = {
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(6, 14, 50, 0.9)',
                borderColor: 'rgba(0, 180, 255, 0.4)',
                textStyle: { color: '#e0f0ff', fontSize: 12 },
            },
            grid: {
                left: 40, right: 25, top: 20, bottom: 30,
            },
            xAxis: {
                type: 'category',
                data: [],
                axisLine: { lineStyle: { color: 'rgba(0,150,220,0.3)' } },
                axisLabel: { color: '#8ab4d6', fontSize: 9, rotate: 20 },
            },
            yAxis: {
                type: 'value',
                name: '出行量(次)',
                nameTextStyle: { color: '#8ab4d6', fontSize: 10 },
                axisLabel: { color: '#8ab4d6', fontSize: 10 },
                splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
            },
            series: [{
                type: 'bar',
                data: [],
                barWidth: '50%',
                itemStyle: {
                    borderRadius: [3, 3, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#00d4ff' },
                        { offset: 1, color: 'rgba(0, 100, 200, 0.6)' },
                    ]),
                },
                label: {
                    show: true,
                    position: 'top',
                    color: '#c0e8ff',
                    fontSize: 10,
                },
            }],
        };
        periodChart.setOption(option);
        console.log('[Realtime] 时段对比图初始化完成');
    }

    // ================================================================
    // 4. KPI 卡片更新
    // ================================================================
    function updateKPIs(data) {
        if (!data) return;
        var setVal = function(id, val) {
            var el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setVal('kpi-trips', (data.total_trips || 0).toLocaleString());
        setVal('kpi-vehicles', (data.total_vehicles || 0).toLocaleString());
        setVal('kpi-duration', (data.avg_duration || 0).toFixed(1));
        setVal('kpi-distance', (data.avg_distance || 0).toFixed(2));
        setVal('kpi-speed', (data.avg_speed || 0).toFixed(1));
    }

    // ================================================================
    // 5. 热力图更新
    // ================================================================
    function updateHeatmap(dataList) {
        if (!heatLayer || !dataList || !dataList.length) return;
        // Leaflet.Heat 格式: [[lat, lng, intensity], ...]
        var points = dataList.map(function(d) {
            return [d.lat, d.lng, Math.min(d.count, 50)];
        });
        heatLayer.setLatLngs(points);
        console.log('[Realtime] 热力图更新: ' + points.length + ' 个点');
    }

    // ================================================================
    // 6. 排行列表更新
    // ================================================================
    function updateRanking(dataList) {
        rankingData = dataList || [];
        var container = document.getElementById('ranking-list');
        if (!container) return;

        if (!rankingData.length) {
            container.innerHTML = '<div class="loading-sm">暂无排行数据</div>';
            return;
        }

        var maxVal = rankingData[0] ? rankingData[0].count : 1;

        var html = rankingData.map(function(item, i) {
            var rankClass = i === 0 ? 'top1' : (i === 1 ? 'top2' : (i === 2 ? 'top3' : 'normal'));
            var barPct = Math.round((item.count / maxVal) * 100);
            return '<div class="rank-item" data-lng="' + item.lng + '" data-lat="' + item.lat + '">' +
                   '<span class="rank-num ' + rankClass + '">' + (i + 1) + '</span>' +
                   '<div class="rank-info">' +
                   '<div class="rank-name">(' + item.lng.toFixed(3) + ', ' + item.lat.toFixed(3) + ')</div>' +
                   '<div class="rank-bar-wrap">' +
                   '<div class="rank-bar-fill" style="width:' + barPct + '%"></div>' +
                   '</div>' +
                   '</div>' +
                   '<span class="rank-value">' + item.count + '</span>' +
                   '</div>';
        }).join('');

        container.innerHTML = html;

        // 点击排行项 → 地图飞到对应位置
        container.querySelectorAll('.rank-item').forEach(function(el) {
            el.addEventListener('click', function() {
                var lng = parseFloat(this.getAttribute('data-lng'));
                var lat = parseFloat(this.getAttribute('data-lat'));
                if (map && !isNaN(lng) && !isNaN(lat)) {
                    map.flyTo([lat, lng], 15, { duration: 1.2 });
                }
            });
        });

        console.log('[Realtime] 排行榜更新: ' + rankingData.length + ' 项');
    }

    // ================================================================
    // 7. 趋势图更新
    // ================================================================
    function updateTrendChart(data) {
        if (!trendChart || !data) return;
        trendChart.setOption({
            xAxis: { data: data.hours || [] },
            series: [
                { data: data.trips || [] },
                { data: data.speeds || [] },
            ],
        });
        console.log('[Realtime] 趋势图更新: ' + (data.hours || []).length + ' 个时段');
    }

    // ================================================================
    // 8. 时段对比图更新
    // ================================================================
    function updatePeriodChart(data) {
        if (!periodChart || !data) return;
        periodChart.setOption({
            xAxis: { data: data.labels || [] },
            series: [{ data: data.values || [] }],
        });
        console.log('[Realtime] 时段对比图更新');
    }

    // ================================================================
    // 9. 时钟更新
    // ================================================================
    function updateClock() {
        var el = document.getElementById('clock');
        if (!el) return;
        var now = new Date();
        var s = now.getFullYear() + '-' +
                String(now.getMonth() + 1).padStart(2, '0') + '-' +
                String(now.getDate()).padStart(2, '0') + ' ' +
                String(now.getHours()).padStart(2, '0') + ':' +
                String(now.getMinutes()).padStart(2, '0') + ':' +
                String(now.getSeconds()).padStart(2, '0');
        el.textContent = '🕐 ' + s;
    }

    // ================================================================
    // 10. 数据获取与渲染
    // ================================================================
    function fetchAllData() {
        // 并行获取所有数据
        API.get('/api/realtime/dashboard').then(function(data) {
            if (!data || data.error) {
                console.warn('[Realtime] 数据获取失败:', data && data.error);
                return;
            }
            updateKPIs(data.kpis);
            updateHeatmap(data.heatmap);
            updateRanking(data.ranking);
            updateTrendChart(data.trend);
            updatePeriodChart(data.period);
        });
    }

    // ================================================================
    // 11. 窗口自适应
    // ================================================================
    function handleResize() {
        if (map) map.invalidateSize();
        if (trendChart) trendChart.resize();
        if (periodChart) periodChart.resize();
    }

    // ================================================================
    // 12. 启动
    // ================================================================
    function boot() {
        console.log('[Realtime] 初始化实时运行态势大屏...');

        // 初始化地图
        initMap();

        // 初始化图表
        initTrendChart();
        initPeriodChart();

        // 首次加载数据
        fetchAllData();

        // 定时刷新
        autoRefreshTimer = setInterval(function() {
            fetchAllData();
            updateClock();
        }, REFRESH_INTERVAL);

        // 时钟每秒更新
        setInterval(updateClock, 1000);
        updateClock();

        // resize 处理
        window.addEventListener('resize', function() {
            clearTimeout(window._resizeTimer);
            window._resizeTimer = setTimeout(handleResize, 200);
        });

        console.log('[Realtime] 大屏初始化完成, 刷新间隔: ' + (REFRESH_INTERVAL / 1000) + 's');
    }

    // DOM 就绪后启动
    window.addEventListener('DOMContentLoaded', boot);

})();
