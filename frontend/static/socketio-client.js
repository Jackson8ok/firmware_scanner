/**
 * 固件漏洞扫描平台 - Socket.IO 实时通知客户端（v2.3）
 * 
 * 功能:
 * - 自动连接和重连
 * - 任务进度实时更新
 * - 队列状态同步
 * - 错误处理和消息提示
 * - 多任务同时监控
 * - 连接状态可视化指示器
 */

// ============================================================
// Socket.IO 管理器类
// ============================================================
class SocketIOManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        
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
        
        this.connected = false;
        
        this.init();
    }
    
    /**
     * 初始化 Socket.IO 连接
     */
    init() {
        // 检测 Socket.IO 支持
        if (typeof io === 'undefined') {
            console.error('❌ Socket.IO 库未加载，请确保引入了 socket.io-client');
            this.notifyError('Socket.IO 库未加载');
            return;
        }
        
        // 配置连接参数
        const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
        const host = window.location.host || 'localhost:8000';
        
        const url = `${protocol}//${host}`;
        
        console.log('📡 Socket.IO 地址:', url);
        
        this.connect(url);
    }
    
    /**
     * 建立 Socket.IO 连接
     */
    connect(url) {
        try {
            console.log('🔌 正在连接 Socket.IO...');
            
            this.socket = io(url, {
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000,
                timeout: 20000,
                autoConnect: true
            });
            
            // 连接成功
            this.socket.on('connect', () => {
                const socketId = this.socket.id;
                console.log(`✅ Socket.IO 连接成功 (ID: ${socketId})`);
                this.connected = true;
                this.reconnectAttempts = 0;
                
                // 更新 UI 连接状态
                this.updateConnectionStateUI('connected', socketId);
                
                // 触发监听器
                this.triggerListeners('onConnected', { socketId });
                
                // 重新订阅所有活跃任务
                this.resubscribeAllTasks();
            });
            
            // 接收初始任务列表
            this.socket.on('initial_tasks', (data) => {
                console.log('📨 收到初始任务列表:', data.tasks?.length || 0);
                
                if (typeof refreshQueueStats === 'function' && data.tasks) {
                    // 通知 app.js 刷新队列状态
                    window.dispatchEvent(new CustomEvent('socketio_initial_tasks', { 
                        detail: { tasks: data.tasks } 
                    }));
                }
            });
            
            // 进度更新
            this.socket.on('scan_progress', (data) => {
                console.log('📊 进度更新:', data);
                this.handleProgressUpdate(data);
            });
            
            // 任务完成
            this.socket.on('scan_completed', (data) => {
                console.log('✅ 任务完成:', data);
                this.handleTaskCompleted(data);
            });
            
            // 任务失败
            this.socket.on('scan_failed', (data) => {
                console.error('❌ 任务失败:', data);
                this.handleTaskFailed(data);
            });
            
            // 连接断开
            this.socket.on('disconnect', (reason) => {
                console.log(`⚠️ Socket.IO 断开 (${reason})`);
                this.connected = false;
                
                // 更新 UI
                this.updateConnectionStateUI('disconnected');
                
                this.triggerListeners('onDisconnected', { reason });
            });
            
            // 重连开始
            this.socket.on('reconnect_attempt', (attemptNumber) => {
                console.log(`🔄 尝试重连 (${attemptNumber}/${this.maxReconnectAttempts})`);
                this.reconnectAttempts = attemptNumber;
                this.updateConnectionStateUI('reconnecting');
            });
            
            // 重连成功
            this.socket.on('reconnect', (attemptNumber) => {
                console.log(`✅ 重连成功 (第 ${attemptNumber} 次)`);
                this.connected = true;
                this.updateConnectionStateUI('connected', this.socket.id);
                this.resubscribeAllTasks();
            });
            
            // 重连失败
            this.socket.on('reconnect_error', (error) => {
                console.error('❌ 重连失败:', error);
            });
            
            // 无法重连
            this.socket.on('reconnect_failed', () => {
                console.error('❌ 重连失败，停止重试');
                this.connected = false;
                this.updateConnectionStateUI('failed');
                this.notifyError('WebSocket 连接失败，请刷新页面');
            });
            
            // 错误
            this.socket.on('connect_error', (error) => {
                console.error('❌ 连接错误:', error.message);
            });
            
            // 通用消息监听器
            this.socket.onAny((event, ...args) => {
                if (event !== 'connect' && event !== 'disconnect') {
                    this.triggerListeners('onMessage', { event, data: args[0] });
                }
            });
            
        } catch (error) {
            console.error('❌ 创建 Socket.IO 连接失败:', error);
            this.notifyError('无法建立 WebSocket 连接');
        }
    }
    
    /**
     * 处理进度更新
     */
    handleProgressUpdate(data) {
        const { task_id, filename, progress, stage, details } = data;
        
        console.log(`📊 ${filename}: ${progress}% - ${stage}`);
        
        // 更新 UI
        this.updateTaskProgressUI(task_id, filename, progress, stage, details);
        
        // 触发监听器
        this.triggerListeners('onProgressUpdate', data);
    }
    
    /**
     * 处理任务完成
     */
    handleTaskCompleted(data) {
        const { task_id, filename, result } = data;
        
        console.log(`✅ ${filename} 完成!`);
        
        // 移除活跃任务标记
        this.activeTasks.delete(task_id);
        
        // 更新 UI
        this.updateTaskStatusUI(task_id, 'completed', result);
        
        // 显示成功通知
        if (window.DashboardState) {
            DashboardState.showToast(`✅ ${filename} 扫描完成!`, 'success');
        } else {
            alert(`${filename} 扫描完成!`);
        }
        
        // 触发监听器
        this.triggerListeners('onStatusChange', {
            taskId: task_id,
            status: 'completed',
            result
        });
        
        // 延迟刷新结果页面
        setTimeout(() => {
            if (typeof loadTaskResult === 'function') {
                loadTaskResult(task_id);
            }
            // 刷新队列统计和图表
            if (typeof refreshQueueStats === 'function') {
                refreshQueueStats();
            }
            if (typeof loadScanHistory === 'function') {
                loadScanHistory();
            }
        }, 1000);
    }
    
    /**
     * 处理任务失败
     */
    handleTaskFailed(data) {
        const { task_id, filename, error_message } = data;
        
        console.error(`❌ ${filename} 失败:`, error_message);
        
        // 移除活跃任务标记
        this.activeTasks.delete(task_id);
        
        // 更新 UI
        this.updateTaskStatusUI(task_id, 'failed', null, error_message);
        
        // 显示错误通知
        const errorMsg = error_message?.split('\n')[0] || '未知错误';
        if (window.DashboardState) {
            DashboardState.showToast(`❌ ${filename} 失败：${errorMsg}`, 'error');
        } else {
            alert(`${filename} 失败：${errorMsg}`);
        }
        
        // 触发监听器
        this.triggerListeners('onError', {
            taskId: task_id,
            error: errorMsg
        });
    }
    
    /**
     * 更新任务进度 UI
     */
    updateTaskProgressUI(taskId, filename, progress, stage, details) {
        // 方法 1: 查找特定的任务元素（如果有）
        let taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
        
        // 方法 2: 如果没有特定元素，更新全局进度条
        if (!taskElement) {
            const globalProgressBar = document.querySelector('.progress-bar');
            const globalProgressText = document.querySelector('.progress-text');
            const globalStatusSection = document.getElementById('taskStatusSection');
            
            if (globalProgressBar && globalProgressText && globalStatusSection) {
                // 显示任务信息
                globalProgressText.textContent = `${progress}% - ${stage}: ${details || ''}`;
                
                // 更新进度条宽度
                globalProgressBar.style.width = `${progress}%`;
                
                // 根据进度改变颜色
                if (progress < 30) {
                    globalProgressBar.style.backgroundColor = '#ffc107'; // 黄色
                    globalProgressBar.classList.add('progress-waiting');
                    globalProgressBar.classList.remove('progress-scanning', 'progress-security', 'progress-done');
                } else if (progress < 70) {
                    globalProgressBar.style.backgroundColor = '#17a2b8'; // 蓝色
                    globalProgressBar.classList.add('progress-scanning');
                    globalProgressBar.classList.remove('progress-waiting', 'progress-security', 'progress-done');
                } else {
                    globalProgressBar.style.backgroundColor = '#28a745'; // 绿色
                    globalProgressBar.classList.add('progress-security');
                    globalProgressBar.classList.remove('progress-waiting', 'progress-scanning', 'progress-done');
                }
            }
        }
        
        // 如果找到任务元素，更新它
        if (taskElement) {
            const progressBar = taskElement.querySelector('.progress-bar');
            const progressText = taskElement.querySelector('.progress-text');
            
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
            
            if (progressText) {
                progressText.textContent = `${progress}% - ${stage}: ${details || ''}`;
            }
        }
    }
    
    /**
     * 更新任务状态 UI
     */
    updateTaskStatusUI(taskId, status, result, errorMessage) {
        const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
        
        if (taskElement) {
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
        }
    }
    
    /**
     * 更新连接状态 UI
     */
    updateConnectionStateUI(state, socketId = null) {
        // 查找连接状态指示器
        const indicator = document.getElementById('wsConnectionIndicator');
        
        if (indicator) {
            // 移除旧的状态类
            indicator.classList.remove('ws-connected', 'ws-disconnected', 'ws-reconnecting', 'ws-failed');
            
            // 添加新的状态类
            switch (state) {
                case 'connected':
                    indicator.classList.add('ws-connected');
                    indicator.title = `已连接 (Socket ID: ${socketId?.substring(0, 8)})`;
                    break;
                case 'disconnected':
                    indicator.classList.add('ws-disconnected');
                    indicator.title = '未连接';
                    break;
                case 'reconnecting':
                    indicator.classList.add('ws-reconnecting');
                    indicator.title = `正在重连 (${this.reconnectAttempts})`;
                    break;
                case 'failed':
                    indicator.classList.add('ws-failed');
                    indicator.title = '连接失败';
                    break;
            }
        }
        
        // 在控制台也输出状态
        const stateText = {
            'connected': '✅ Connected',
            'disconnected': '⚠️ Disconnected',
            'reconnecting': '🔄 Reconnecting...',
            'failed': '❌ Failed'
        };
        console.log(`📡 WebSocket State: ${stateText[state]}`);
    }
    
    /**
     * 订阅特定任务的更新
     */
    subscribe(taskId) {
        if (!this.socket || !this.socket.connected) {
            console.warn('⚠️ Socket.IO 未连接，无法订阅');
            return;
        }
        
        this.activeTasks.add(taskId);
        
        // 发送订阅消息（虽然服务器会自动推送所有任务，但这里保留接口）
        this.socket.emit('subscribe', { task_id: taskId });
        
        console.log(`📝 已订阅任务：${taskId}`);
    }
    
    /**
     * 取消订阅任务
     */
    unsubscribe(taskId) {
        this.activeTasks.delete(taskId);
        
        if (this.socket && this.socket.connected) {
            this.socket.emit('unsubscribe', { task_id: taskId });
        }
        
        console.log(`❌ 取消订阅任务：${taskId}`);
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
     * 获取连接状态
     */
    getConnectionState() {
        if (!this.socket) return 'not_initialized';
        if (!this.connected) return 'disconnected';
        
        const states = {
            'connecting': 'connecting',
            'connected': 'connected',
            'disconnecting': 'disconnecting',
            'disconnected': 'disconnected'
        };
        
        return states[this.socket.io.engine.state] || 'unknown';
    }
    
    /**
     * 优雅关闭连接
     */
    close() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        this.connected = false;
        console.log('👋 Socket.IO 已关闭');
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
}

// ============================================================
// 全局实例
// ============================================================
let socketIOManager = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否已加载 Socket.IO 客户端库
    if (typeof io === 'undefined') {
        console.error('❌ Socket.IO 客户端库未加载');
        
        // 尝试动态加载
        const script = document.createElement('script');
        script.src = '/socket.io/socket.io.js';
        script.onload = () => {
            console.log('✅ Socket.IO 客户端库已加载');
            socketIOManager = new SocketIOManager();
            window.socketIOManager = socketIOManager;
        };
        script.onerror = () => {
            console.error('❌ 无法加载 Socket.IO 客户端库');
        };
        document.head.appendChild(script);
    } else {
        // Socket.IO 已加载，直接初始化
        socketIOManager = new SocketIOManager();
        window.socketIOManager = socketIOManager;
        console.log('✅ Socket.IO Manager 已初始化');
    }
});

// ============================================================
// 便捷函数
// ============================================================

/**
 * 订阅任务更新
 */
function subscribeToTaskSO(taskId) {
    if (socketIOManager) {
        socketIOManager.subscribe(taskId);
    }
}

/**
 * 取消订阅任务
 */
function unsubscribeFromTaskSO(taskId) {
    if (socketIOManager) {
        socketIOManager.unsubscribe(taskId);
    }
}

/**
 * 获取 Socket.IO 连接状态
 */
function getSocketIOState() {
    return socketIOManager ? socketIOManager.getConnectionState() : 'not_initialized';
}

// 导出到全局
window.SocketIOManager = SocketIOManager;
window.socketIOManager = socketIOManager;
window.subscribeToTaskSO = subscribeToTaskSO;
window.unsubscribeFromTaskSO = unsubscribeFromTaskSO;
window.getSocketIOState = getSocketIOState;
