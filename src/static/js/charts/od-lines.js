/**
 * 深圳地图 OD 出行流向图
 * 数据源: /api/od-flows
 *
 * ECharts geo + graph 系列, 本地 GeoJSON 优先, CDN 回退
 * 不使用 shine 主题 (暗色背景与地图亮色配色冲突)
 */
(function() {
    'use strict';

    // 深圳 GeoJSON — 本地优先，CDN 回退
    var SZ_GEO_LOCAL = '/static/geo/shenzhen.json';
    var SZ_GEO_CDN   = 'https://geo.datav.aliyun.com/areas_v3/bound/440300_full.json';
    var MAP_NAME     = 'shenzhen';
    var SZ_ROUGH_LAT = 22.55;

    var _jsonReady   = false;
    var _loading     = false;
    var _pendingData = null;   // GeoJSON 加载完成前缓存的数据
    var _loadError   = null;   // 加载错误信息

    // --------------- 入口 ---------------

    function render(domId, data) {
        var dom = document.getElementById(domId);
        if (!dom) {
            console.warn('[OD-Flow] DOM 不存在:', domId);
            return;
        }

        if (!data || !data.nodes || !data.nodes.length) {
            _showMessage(dom, 'error', '深圳OD流向图 — 无数据');
            console.warn('[OD-Flow] 数据为空');

            // 写入本地日志
            if (window.__odFlowLog) {
                window.__odFlowLog.push({ time: new Date().toISOString(), type: 'no-data', detail: JSON.stringify(data) });
            }
            return;
        }

        console.log('[OD-Flow] 收到数据: nodes=' + data.nodes.length + ', edges=' + data.edges.length);

        // GeoJSON 还没加载好 → 缓存数据, 先加载地图
        if (!_jsonReady) {
            _pendingData = { domId: domId, data: data };
            _showMessage(dom, 'loading', '正在加载深圳地图 GeoJSON…');
            _loadGeoJSON();
            return;
        }

        _doRender(domId, data);
    }

    // --------------- GeoJSON 加载 ---------------

    function _loadGeoJSON() {
        if (_jsonReady) return;
        if (_loading) return;
        _loading = true;
        _loadError = null;

        console.log('[OD-Flow] 开始加载深圳 GeoJSON (本地优先)…');

        // 先尝试本地文件
        _tryLoad(SZ_GEO_LOCAL, function onLocalOK(geoJSON) {
            console.log('[OD-Flow] 深圳 GeoJSON 加载成功 (本地)');
            _onGeoReady(geoJSON);
        }, function onLocalFail(err) {
            console.warn('[OD-Flow] 本地 GeoJSON 不可用, 尝试 CDN…', err);
            // 本地失败 → CDN 回退
            _tryLoad(SZ_GEO_CDN, function onCDNOK(geoJSON) {
                console.log('[OD-Flow] 深圳 GeoJSON 加载成功 (CDN)');
                _onGeoReady(geoJSON);
            }, function onCDNFail(err2) {
                console.error('[OD-Flow] GeoJSON 加载失败 (本地+CDN 均不可用)', err2);
                _loadError = '深圳地图加载失败: 本地和CDN均不可用';
                _loading = false;

                // 给等待中的 DOM 显示错误
                if (_pendingData) {
                    var dom = document.getElementById(_pendingData.domId);
                    _showMessage(dom, 'error', _loadError);
                }
            });
        });
    }

    function _tryLoad(url, onSuccess, onError) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.timeout = 15000;

        xhr.onload = function() {
            if (xhr.status === 200 || xhr.status === 304) {
                try {
                    var geoJSON = JSON.parse(xhr.responseText);
                    if (geoJSON && geoJSON.type === 'FeatureCollection') {
                        onSuccess(geoJSON);
                    } else {
                        onError('Invalid GeoJSON: type=' + (geoJSON && geoJSON.type));
                    }
                } catch (e) {
                    onError('JSON parse error: ' + e.message);
                }
            } else {
                onError('HTTP ' + xhr.status);
            }
        };

        xhr.ontimeout = function() {
            onError('Timeout (15s)');
        };

        xhr.onerror = function() {
            onError('Network error');
        };

        xhr.send();
    }

    function _onGeoReady(geoJSON) {
        echarts.registerMap(MAP_NAME, geoJSON);
        _jsonReady = true;
        _loading = false;

        // 渲染等待中的数据
        if (_pendingData) {
            var pd = _pendingData;
            _pendingData = null;
            _doRender(pd.domId, pd.data);
        }
    }

    // --------------- ECharts 渲染 ---------------

    function _doRender(domId, data) {
        var dom = document.getElementById(domId);
        if (!dom) { console.warn('[OD-Flow] DOM 消失:', domId); return; }

        // ★ 不使用 shine 暗色主题, 否则浅色地图不可见
        var instance;
        try {
            // 先销毁可能存在的旧实例 (如果之前用 shine 初始化过)
            if (window.ChartManager && window.ChartManager.instances && window.ChartManager.instances[domId]) {
                window.ChartManager.instances[domId].dispose();
                delete window.ChartManager.instances[domId];
            }
            instance = echarts.init(dom);
        } catch (e) {
            console.error('[OD-Flow] ECharts 初始化失败:', e);
            _showMessage(dom, 'error', '图表引擎初始化失败: ' + e.message);
            return;
        }

        if (!instance) {
            _showMessage(dom, 'error', '图表初始化失败 (null instance)');
            return;
        }

        // 注册到 ChartManager (以便 resize)
        if (window.ChartManager && window.ChartManager.instances) {
            window.ChartManager.instances[domId] = instance;
        }

        try {
            instance.setOption({
                title: {
                    text: '深圳市出租车 OD 出行流向',
                    subtext: 'Top-30 OD对 | 箭头表示行驶方向 | 深圳市区行政区划',
                    left: 'center',
                    top: 8,
                    textStyle: { color: '#333', fontSize: 15 },
                    subtextStyle: { color: '#888', fontSize: 11 }
                },
                tooltip: {
                    trigger: 'item',
                    formatter: function(p) {
                        if (p.dataType === 'edge') {
                            return '<b>' + p.data.source + '</b><br/>'
                                 + '&darr;<br/>'
                                 + '<b>' + p.data.target + '</b>';
                        }
                        if (p.value && Array.isArray(p.value) && p.value.length >= 2) {
                            return '<b>' + p.name + '</b><br/>'
                                 + '坐标: [' + p.value[0].toFixed(5)
                                 + ', ' + p.value[1].toFixed(5) + ']';
                        }
                        return '<b>' + (p.name || '') + '</b>';
                    }
                },
                geo: {
                    map: MAP_NAME,
                    roam: true,
                    aspectScale: Math.cos((SZ_ROUGH_LAT * Math.PI) / 180),
                    zoom: 1.1,
                    center: [114.05, 22.60],
                    label: { show: false },
                    itemStyle: {
                        areaColor: '#f5f5f5',
                        borderColor: '#bbb',
                        borderWidth: 1
                    },
                    emphasis: {
                        disabled: true,
                        itemStyle: { areaColor: '#e0e0e0' }
                    }
                },
                series: [{
                    type: 'graph',
                    coordinateSystem: 'geo',
                    data: data.nodes,
                    edges: data.edges,
                    roam: true,
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: [0, 8],
                    symbol: 'circle',
                    symbolSize: 7,
                    itemStyle: {
                        color: '#e65100',
                        borderColor: '#fff',
                        borderWidth: 1.5
                    },
                    label: {
                        show: true,
                        fontSize: 7,
                        color: '#555',
                        position: 'top',
                        distance: 3,
                        formatter: function(p) {
                            return p.name.length > 20
                                ? p.name.substring(0, 18) + '…'
                                : p.name;
                        }
                    },
                    lineStyle: {
                        color: '#1565c0',
                        opacity: 0.55,
                        curveness: 0.2,
                        width: 1.5
                    },
                    emphasis: {
                        focus: 'adjacency',
                        lineStyle: { width: 3, opacity: 0.9 },
                        itemStyle: { color: '#c62828', borderWidth: 2.5 }
                    }
                }]
            });

            console.log('[OD-Flow] 渲染成功: ' + data.nodes.length + ' nodes, ' + data.edges.length + ' edges');

        } catch (e) {
            console.error('[OD-Flow] setOption 失败:', e.message, e.stack);
            _showMessage(dom, 'error', 'OD流向图渲染失败: ' + e.message.replace(/</g, '&lt;'));
        }
    }

    // --------------- 辅助 ---------------

    function _showMessage(dom, type, msg) {
        if (!dom) return;
        var cls = (type === 'error') ? 'error-state' : 'loading';
        dom.innerHTML = '<div class="' + cls + '">' + msg + '</div>';
    }

    // 暴露到全局
    window.ODLinesChart = { render: render };
})();
