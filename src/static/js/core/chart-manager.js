/**
 * ECharts 图表实例管理器
 * 统一管理所有图表的初始化（应用 shine 主题）、销毁和自适应
 */
(function() {
    'use strict';

    var instances = {};  // { domId: echartsInstance }

    /**
     * 获取或创建 ECharts 实例（自动应用 shine 主题）
     * @param {string} domId - DOM 元素 ID
     * @returns {object} echarts 实例
     */
    function init(domId) {
        if (instances[domId]) {
            return instances[domId];
        }
        var dom = document.getElementById(domId);
        if (!dom) {
            console.error('[ChartManager] DOM 元素不存在:', domId);
            return null;
        }
        // 使用 shine 主题初始化
        var instance = echarts.init(dom, 'shine');
        instances[domId] = instance;
        return instance;
    }

    /**
     * 销毁指定图表实例
     */
    function dispose(domId) {
        if (instances[domId]) {
            instances[domId].dispose();
            delete instances[domId];
        }
    }

    /**
     * 窗口 resize 时自适应所有图表
     */
    function resizeAll() {
        Object.keys(instances).forEach(function(id) {
            try {
                instances[id].resize();
            } catch(e) {
                // 忽略已销毁的实例
            }
        });
    }

    window.ChartManager = {
        init: init,
        dispose: dispose,
        resizeAll: resizeAll,
        instances: instances
    };
})();
