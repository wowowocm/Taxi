/**
 * API 请求封装
 * 所有数据获取统一通过此模块，便于错误处理和配置管理
 */
(function() {
    'use strict';

    var BASE = '';  // 同源 API，无需额外前缀

    /**
     * GET 请求 JSON 数据
     * @param {string} endpoint - API 路径，如 '/api/hourly'
     * @returns {Promise<object|null>} 成功返回解析后的 JSON，失败返回 null
     */
    function get(endpoint) {
        return fetch(BASE + endpoint)
            .then(function(resp) {
                if (!resp.ok) {
                    throw new Error('HTTP ' + resp.status + ' ' + endpoint);
                }
                return resp.json();
            })
            .catch(function(err) {
                console.error('[API] 请求失败:', endpoint, err.message);
                return null;  // 降级：不阻塞其他图表
            });
    }

    window.API = { get: get };
})();
