/**
 * 固件漏洞扫描平台 - WebSocket 实时通知客户端
 * 
 * 功能:
 * - 自动连接和重连
 * - 任务进度实时更新
 * - 队列状态同步
 * - 错误处理和消息提示
 * - 多任务同时监控
 */

// ============================================================
// WebSocket 管理器类
// ============================================================
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.url = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 初始延迟 1ms
        this.maxReconnectDelay = 30000; // 最大延迟 30s
        
        this.activeTasks = new Set();
        this.listeners = {
            onProgressUpdate: [],
            onStatusChange: [],
            onQueueStats: [],
            onError: [],
            onConnected: [],
            onDisconnected: [],
            onMessage: []
        };
        
        this.healthCheckInterval = null;
        this.pingInterval = null;
        
        this.init();
    }
    
    /**
     * 初始化 WebSocket 连接
     */
    init() {
        // 检测 WebSocket 支持
        if (!('WebSocket' in window)) {
            console.error('❌ WebSocket 不支持，请使用现代浏览器');
            this.notifyError('您的浏览器不支持 WebSocket');
            return;
        }
        
        // 从配置读取或默认值
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.hostname || 'localhost';
        const wsPort = 8765; // WebSocket 服务器端口
        
        this.url = `${wsProtocol}//${wsHost}:${wsPort}/ws`;
        
        console.log('📡 WebSocket 地址:', this.url);
        
        this.connect();
    }
    
    /**
     * 建立 WebSocket 连接
     */
    connect() {
        try {
            console.log('🔌 正在连接 WebSocket...');
            
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket 连接成功');
                this.reconnectAttempts = 0;
                this.triggerListeners('onConnected', {});
                
                // 开始心跳检查
                this.startHeartbeat();
                
                // 重新订阅所有活跃任务
                this.resubscribeAllTasks();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('❌ 解析消息失败:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('❌ WebSocket 错误:', error);
                this.notifyError('WebSocket 连接错误');
            };
            
            this.ws.onclose = (event) => {
                console.log(`⚠️ WebSocket 断开 (代码：${event.code}, 原因：${event.reason})`);
                this.triggerListeners('onDisconnected', event);
                
                // 停止心跳
                this.stopHeartbeat();
                
                // 尝试重连
                this.attemptReconnect();
            };
            
        } catch (error) {
            console.error('❌ 创建 WebSocket 连接失败:', error);
            this.attemptReconnect();
        }
    }
    
    /**
     * 处理接收到的消息
     */
    handleMessage(message) {
        const { type, task_id, progress, status, stats, error } = message;
        
        console.log('📨 收到 WebSocket 消息:', type);
        
        // 触发全局消息监听器
        this.triggerListeners('onMessage', message);
        
        switch (type) {
            case 'progress_update':
                this.handleProgressUpdate(task_id, progress, message.message, message.details);
                break;
                
            case 'status_change':
                this.handleStatusChange(task_id, status, message.result);
                break;
                
            case 'queue_stats':
                this.handleQueueStats(stats);
                break;
                
            case 'error':
                this.handleError(task_id, error);
                break;
                
            case 'pong':
                // 心跳响应，不需要特殊处理
                break;
                
            default:
                console.log('🤷 未知消息类型:', type);
        }
    }
    
    /**
     * 处理进度更新
     */
    handleProgressUpdate(taskId, progress, message, details) {
        console.log(`📊 任务 ${taskId} 进度: ${progress}% - ${message}`);
        
        // 更新 UI
        this.updateTaskProgressUI(taskId, progress, message);
        
        // 触发监听器
        this.triggerListeners('onProgressUpdate', {
            taskId,
            progress,
            message,
            details
        });
    }
    
    /**
     * 处理状态变更
     */
    handleStatusChange(taskId, status, result) {
        console.log(`🔄 任务 ${taskId} 状态变更: ${status}`);
        
        // 更新 UI
        this.updateTaskStatusUI(taskId, status, result);
        
        // 如果任务完成，移除活跃任务标记
        if (status === 'completed' || status === 'failed') {
            this.activeTasks.delete(taskId);
        }
        
        // 触发监听器
        this.triggerListeners('onStatusChange', {
            taskId,
            status,
            result
        });
    }
    
    /**
     * 处理队列统计
     */
    handleQueueStats(stats) {
        console.log('📈 队列统计更新:', stats);
        
        // 更新 UI
        this.updateQueueStatsUI(stats);
        
        // 触发监听器
        this.triggerListeners('onQueueStats', stats);
    }
    
    /**
     * 处理错误
     */
    handleError(taskId, errorMessage) {
        console.error(`❌ 任务 ${taskId} 错误:`, errorMessage);
        
        // 显示错误通知
        if (window.DashboardState) {
            DashboardState.showToast(`任务 ${taskId} 失败：${errorMessage}`, 'error');
        } else {
            alert(`任务失败：${errorMessage}`);
        }
        
        // 触发监听器
        this.triggerListeners('onError', {
            taskId,
            error: errorMessage
        });
    }
    
    /**
     * 更新任务进度 UI
     */
    updateTaskProgressUI(taskId, progress, message) {
        // 查找对应的任务元素
        const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
        
        if (taskElement) {
            // 更新进度条
            const progressBar = taskElement.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
            
            // 更新进度文本
            const progressText = taskElement.querySelector('.progress-text');
            if (progressText) {
                progressText.textContent = `${progress}% - ${message}`;
            }
            
            // 根据进度改变颜色
            if (progressBar) {
                if (progress < 30) {
                    progressBar.style.backgroundColor = '#ffc107'; // 黄色
                } else if (progress < 70) {
                    progressBar.style.backgroundColor = '#17a2b8'; // 蓝色
                } else {
                    progressBar.style.backgroundColor = '#28a745'; // 绿色
                }
            }
        }
        
        // 如果没有特定的任务元素，在任务列表中添加或更新
        const taskList = document.getElementById('activeTasks');
        if (taskList && !document.querySelector(`[data-task-id="${taskId}"]`)) {
            this.addTaskToUI(taskId, progress, message);
        }
    }
    
    /**
     * 添加任务到 UI
     */
    addTaskToUI(taskId, progress, message) {
        this.activeTasks.add(taskId);
        
        const taskList = document.getElementById('activeTasks');
        if (!taskList) return;
        
        const taskItem = document.createElement('div');
        taskItem.className = 'task-item running';
        taskItem.setAttribute('data-task-id', taskId);
        taskItem.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <strong>${taskId}</strong>
                <span class="progress-text">${progress}% - ${message}</span>
            </div>
            <div class="progress" style="height: 6px; background: #e9ecef; border-radius: 3px; overflow: hidden;">
                <div class="progress-bar" style="width: ${progress}%; height: 100%; background: #ffc107; transition: width 0.3s;"></div>
            </div>
        `;
        
        taskList.appendChild(taskItem);
    }
    
    /**
     * 更新任务状态 UI
     */
    updateTaskStatusUI(taskId, status, result) {
        const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
        
        if (taskElement) {
            // 根据状态改变样式
            taskElement.classList.remove('running', 'queued', 'completed', 'failed');
            taskElement.classList.add(status);
            
            // 更新状态标签
            const statusSpan = taskElement.querySelector('.status-label');
            if (statusSpan) {
                statusSpan.textContent = status.toUpperCase();
                
                const statusColors = {
                    'pending': '#6c757d',
                    'queued': '#17a2b8',
                    'running': '#ffc107',
                    'completed': '#28a745',
                    'failed': '#dc3545'
                };
                statusSpan.style.color = statusColors[status] || '#6c757d';
            }
            
            // 如果完成，刷新数据
            if (status === 'completed' && result) {
                setTimeout(() => {
                    if (typeof loadTaskResult === 'function') {
                        loadTaskResult(taskId);
                    }
                    
                    if (window.DashboardState) {
                        DashboardState.showToast(`任务 ${taskId} 已完成！`, 'success');
                    }
                }, 500);
            }
        }
    }
    
    /**
     * 更新队列统计 UI
     */
    updateQueueStatsUI(stats) {
        const elements = {
            queuedCount: stats.pending || stats.queued || 0,
            runningCount: stats.running || 0,
            completedCount: stats.completed || 0,
            failedCount: stats.failed || 0
        };
        
        for (const [id, value] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                // 数字动画效果
                const current = parseInt(element.textContent) || 0;
                if (current !== value) {
                    this.animateValue(element, current, value, 500);
                }
            }
        }
    }
    
    /**
     * 数字动画效果
     */
    animateValue(element, start, end, duration) {
        if (!element) return;
        
        const range = end - start;
        let current = start;
        const increment = end > start ? 1 : -1;
        const stepTime = Math.abs(Math.floor(duration / range));
        
        const timer = setInterval(() => {
            current += increment;
            element.textContent = current;
            
            if (current === end) {
                clearInterval(timer);
            }
        }, Math.max(stepTime, 50)); // 最小 50ms
    }
    
    /**
     * 订阅特定任务的更新
     */
    subscribe(taskId) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.warn('⚠️ WebSocket 未连接，无法订阅');
            return;
        }
        
        this.activeTasks.add(taskId);
        
        this.ws.send(JSON.stringify({
            type: 'subscribe',
            task_id: taskId
        }));
        
        console.log(`📝 已订阅任务: ${taskId}`);
    }
    
    /**
     * 取消订阅任务
     */
    unsubscribe(taskId) {
        this.activeTasks.delete(taskId);
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'unsubscribe',
                task_id: taskId
            }));
        }
        
        console.log(`❌ 取消订阅任务: ${taskId}`);
    }
    
    /**
     * 重新订阅所有活跃任务
     */
    resubscribeAllTasks() {
        this.activeTasks.forEach(taskId => {
            this.subscribe(taskId);
        });
    }
    
    /**
     * 尝试重新连接
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ 已达到最大重连次数，停止重试');
            this.notifyError('WebSocket 连接失败，请刷新页面');
            return;
        }
        
        this.reconnectAttempts++;
        
        // 指数退避算法
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
            this.maxReconnectDelay
        );
        
        console.log(`🔄 将在 ${delay/1000}s 后重试 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }
    
    /**
     * 开始心跳检测
     */
    startHeartbeat() {
        // 每 30 秒发送一次 ping
        this.pingInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'ping',
                    timestamp: Date.now()
                }));
            }
        }, 30000);
        
        // 每 10 秒检查连接健康状态
        this.healthCheckInterval = setInterval(() => {
            if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
                console.warn('⚠️ WebSocket 似乎已断开，尝试重连');
                this.attemptReconnect();
            }
        }, 10000);
    }
    
    /**
     * 停止心跳检测
     */
    stopHeartbeat() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
    }
    
    /**
     * 优雅关闭连接
     */
    close() {
        this.stopHeartbeat();
        
        if (this.ws) {
            this.ws.close(1000, '客户端关闭');
            this.ws = null;
        }
        
        console.log('👋 WebSocket 已关闭');
    }
    
    /**
     * 添加监听器
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
    }
    
    /**
     * 移除监听器
     */
    off(event, callback) {
        if (this.listeners[event]) {
            const index = this.listeners[event].indexOf(callback);
            if (index > -1) {
                this.listeners[event].splice(index, 1);
            }
        }
    }
    
    /**
     * 触发监听器
     */
    triggerListeners(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`监听器 ${event} 执行出错:`, error);
                }
            });
        }
    }
    
    /**
     * 显示错误通知
     */
    notifyError(message) {
        if (window.DashboardState) {
            DashboardState.showToast(message, 'error');
        } else {
            console.error(message);
        }
    }
    
    /**
     * 获取连接状态
     */
    getConnectionState() {
        if (!this.ws) return 'disconnected';
        
        const states = {
            0: 'connecting',
            1: 'open',
            2: 'closing',
            3: 'closed'
        };
        
        return states[this.ws.readyState] || 'unknown';
    }
}

// ============================================================
// 全局实例
// ============================================================
let websocketManager = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 稍作延迟，确保其他模块已加载
    setTimeout(() => {
        websocketManager = new WebSocketManager();
        
        // 绑定到全局，方便访问
        window.websocketManager = websocketManager;
        
        console.log('✅ WebSocket Manager 已初始化');
    }, 1000);
});

// ============================================================
// 便捷函数
// ============================================================

/**
 * 订阅任务更新
 */
function subscribeToTask(taskId) {
    if (websocketManager) {
        websocketManager.subscribe(taskId);
    }
}

/**
 * 取消订阅任务
 */
function unsubscribeFromTask(taskId) {
    if (websocketManager) {
        websocketManager.unsubscribe(taskId);
    }
}

/**
 * 获取 WebSocket 连接状态
 */
function getWebSocketState() {
    return websocketManager ? websocketManager.getConnectionState() : 'not_initialized';
}

/**
 * 手动刷新队列状态（备用方案）
 */
function refreshQueueStatsManual() {
    if (typeof refreshQueueStats === 'function') {
        refreshQueueStats();
    }
}

// 导出到全局
window.WebSocketManager = WebSocketManager;
window.websocketManager = websocketManager;
window.subscribeToTask = subscribeToTask;
window.unsubscribeFromTask = unsubscribeFromTask;
window.getWebSocketState = getWebSocketState;
