/**
 * 深圳地图 OD 出行流向图
 * 数据源: /api/od-flows
 *
 * 参考 project_info/rule.md 地理坐标图 —
 *   echarts.registerMap('shenzhen', geoJSON)
 *   + geo { map: 'shenzhen' }
 *   + graph { coordinateSystem: 'geo' }
 *
 * 深圳 GeoJSON 来源:
 *   DataV GeoAtlas — https://geo.datav.aliyun.com/areas_v3/bound/440300_full.json
 *   （行政编码 440300 = 深圳市）
 */
(function() {
    'use strict';

    var SZ_GEO_URL = 'https://geo.datav.aliyun.com/areas_v3/bound/440300_full.json';
    var MAP_NAME = 'shenzhen';
    var _jsonReady = false;
    var _pendingData = null;  // GeoJSON 加载完成前缓存数据

    /**
     * 深圳纬度 ≈ 22.55°
     * Mercator 投影 aspectScale = cos(lat)
     */
    var SZ_ROUGH_LAT = 22.55;

    function render(domId, data) {
        var dom = document.getElementById(domId);
        if (!dom) { console.warn('[Geo-OD] DOM不存在:', domId); return; }

        if (!data || !data.nodes || !data.nodes.length) {
            dom.innerHTML = '<div class="error-state">深圳OD流向图 — 无数据</div>';
            return;
        }

        // 如果 GeoJSON 还未加载，缓存数据等待加载完成后重试
        if (!_jsonReady) {
            _pendingData = { domId: domId, data: data };
            dom.innerHTML = '<div class="loading">正在加载深圳地图…</div>';
            _loadGeoJSON();
            return;
        }

        _doRender(domId, data);
    }

    function _loadGeoJSON() {
        // 防重复加载
        if (_jsonReady) return;
        if (window._sz_geo_loading) return;
        window._sz_geo_loading = true;

        var xhr = new XMLHttpRequest();
        xhr.open('GET', SZ_GEO_URL, true);
        xhr.onload = function() {
            if (xhr.status === 200) {
                try {
                    var geoJSON = JSON.parse(xhr.responseText);
                    echarts.registerMap(MAP_NAME, geoJSON);
                    _jsonReady = true;
                    console.log('[Geo-OD] 深圳地图 GeoJSON 加载成功');
                    // 渲染等待中的数据
                    if (_pendingData) {
                        _doRender(_pendingData.domId, _pendingData.data);
                        _pendingData = null;
                    }
                } catch (e) {
                    console.error('[Geo-OD] GeoJSON 解析失败:', e);
                }
            } else {
                console.error('[Geo-OD] GeoJSON 请求失败: HTTP', xhr.status);
                if (_pendingData) {
                    var dom = document.getElementById(_pendingData.domId);
                    if (dom) dom.innerHTML = '<div class="error-state">深圳地图加载失败 (HTTP ' + xhr.status + ')</div>';
                }
            }
            window._sz_geo_loading = false;
        };
        xhr.onerror = function() {
            console.error('[Geo-OD] GeoJSON 网络错误');
            window._sz_geo_loading = false;
        };
        xhr.send();
    }

    function _doRender(domId, data) {
        var dom = document.getElementById(domId);
        var inst = window.ChartManager.init(domId);
        if (!inst) {
            dom.innerHTML = '<div class="error-state">深圳OD流向图 — 初始化失败</div>';
            return;
        }

        try {
            inst.setOption({
                title: {
                    text: '深圳市出租车 OD 出行流向',
                    subtext: 'Top-30 OD对 | 箭头表示行驶方向',
                    left: 'center',
                    top: 10,
                    textStyle: { color: '#333', fontSize: 16 }
                },
                tooltip: {
                    trigger: 'item',
                    formatter: function(p) {
                        if (p.dataType === 'edge') {
                            return '<b>' + p.data.source + '</b><br/>'
                                 + '&darr;<br/>'
                                 + '<b>' + p.data.target + '</b>';
                        }
                        return '<b>' + p.name + '</b><br/>'
                             + '坐标: [' + (p.value || [0,0])[0].toFixed(4)
                             + ', ' + (p.value || [0,0])[1].toFixed(4) + ']';
                    }
                },
                geo: {
                    map: MAP_NAME,
                    roam: true,
                    aspectScale: Math.cos((SZ_ROUGH_LAT * Math.PI) / 180),
                    label: {
                        show: false
                    },
                    itemStyle: {
                        areaColor: '#f3f4f6',
                        borderColor: '#999',
                        borderWidth: 1
                    },
                    emphasis: {
                        itemStyle: {
                            areaColor: '#e8eaf6'
                        }
                    }
                },
                series: [{
                    type: 'graph',
                    coordinateSystem: 'geo',
                    data: data.nodes,
                    edges: data.edges,
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: 8,
                    symbol: 'circle',
                    symbolSize: 8,
                    itemStyle: {
                        color: '#1a237e',
                        borderColor: '#fff',
                        borderWidth: 1
                    },
                    label: {
                        show: true,
                        fontSize: 8,
                        color: '#333',
                        position: 'top',
                        formatter: function(p) {
                            return p.name.length > 18
                                ? p.name.substring(0, 16) + '…'
                                : p.name;
                        }
                    },
                    lineStyle: {
                        color: '#1a237e',
                        opacity: 0.6,
                        curveness: 0.15
                    },
                    emphasis: {
                        focus: 'adjacency',
                        lineStyle: {
                            width: 3,
                            opacity: 0.9
                        },
                        itemStyle: {
                            color: '#c12e34',
                            borderWidth: 2
                        }
                    }
                }]
            });
        } catch (e) {
            console.error('[Geo-OD] 渲染失败:', e.message);
            dom.innerHTML = '<div class="error-state">深圳OD流向图 渲染失败: '
                          + e.message.replace(/</g, '&lt;') + '</div>';
        }
    }

    window.ODLinesChart = { render: render };
})();
