/**
 * 固件漏洞扫描平台 - 前端增强模块 v2.3
 * 新增功能:
 * - 暗色主题切换
 * - 键盘快捷键
 * - 实时通知系统
 * - 导出优化
 * - 组件可视化
 * - 打印友好视图
 */

// ============================================================
// 全局状态管理
// ============================================================
const DashboardState = {
    theme: localStorage.getItem('theme') || 'light',
    notifications: [],
    currentTask: null,
    componentsData: [],
    vulnerabilitiesData: [],
    filters: {
        severity: 'all',
        component: 'all',
        dateRange: '7',
        compliance: 'all'
    },
    sort: {
        field: 'priority_score',
        direction: 'desc'
    },
    viewMode: 'table', // table, card, list
    
    init() {
        this.applyTheme();
        this.initKeyboardShortcuts();
        this.initNotificationSystem();
        this.initViewToggle();
    },
    
    // ============================================================
    // 主题管理
    // ============================================================
    applyTheme() {
        document.body.setAttribute('data-theme', this.theme);
        this.updateThemeIcons();
    },
    
    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', this.theme);
        this.applyTheme();
        this.showToast(`已切换到${this.theme === 'dark' ? '暗色' : '亮色'}主题`);
    },
    
    updateThemeIcons() {
        const icon = document.getElementById('themeToggleIcon');
        if (icon) {
            icon.textContent = this.theme === 'dark' ? '☀️' : '🌙';
        }
    },
    
    // ============================================================
    // 键盘快捷键
    // ============================================================
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K - 快速搜索
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.showSearchModal();
            }
            
            // Escape - 关闭模态框/取消操作
            if (e.key === 'Escape') {
                this.closeModals();
            }
            
            // / - 打开过滤面板
            if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                e.preventDefault();
                this.toggleFilterPanel();
            }
            
            // N - 新建扫描
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                document.querySelector('.file-input-wrapper label').click();
            }
            
            // R - 刷新数据
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                location.reload();
            }
            
            // S - 保存报告
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.exportReport('pdf');
            }
            
            // E - 导出 Excel
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                this.exportReport('excel');
            }
            
            // H - 显示帮助
            if (e.key === '?') {
                e.preventDefault();
                this.showHelpModal();
            }
        });
    },
    
    showKeyboardHelp() {
        const shortcuts = [
            ['Ctrl+N', '新扫描'],
            ['Ctrl+R', '刷新'],
            ['Ctrl+S', '导出 PDF'],
            ['Ctrl+E', '导出 Excel'],
            ['Ctrl+K', '快速搜索'],
            ['/', '打开过滤器'],
            ['Esc', '关闭弹窗'],
            ['?', '显示帮助']
        ];
        
        const html = `
            <div class="modal">
                <div class="modal-content" style="max-width: 500px;">
                    <h3>⌨️ 键盘快捷键</h3>
                    <table style="width: 100%; margin-top: 20px;">
                        ${shortcuts.map(([key, desc]) => `
                            <tr>
                                <td style="padding: 10px; font-family: monospace; background: #f0f0f0; border-radius: 4px;">
                                    ${key}
                                </td>
                                <td style="padding: 10px;">${desc}</td>
                            </tr>
                        `).join('')}
                    </table>
                    <button class="btn btn-primary" onclick="DashboardState.closeModals()" style="margin-top: 20px;">
                        关闭
                    </button>
                </div>
            </div>
        `;
        
        this.showModal(html);
    },
    
    // ============================================================
    // 通知系统
    // ============================================================
    initNotificationSystem() {
        // 创建通知容器
        const container = document.createElement('div');
        container.id = 'notificationContainer';
        container.className = 'notification-container';
        document.body.appendChild(container);
    },
    
    showToast(message, type = 'info', duration = 3000) {
        const notification = {
            id: Date.now(),
            message,
            type,
            timestamp: new Date()
        };
        
        this.notifications.push(notification);
        this.renderNotifications();
        
        setTimeout(() => {
            this.removeNotification(notification.id);
        }, duration);
        
        return notification.id;
    },
    
    removeNotification(id) {
        this.notifications = this.notifications.filter(n => n.id !== id);
        this.renderNotifications();
    },
    
    renderNotifications() {
        const container = document.getElementById('notificationContainer');
        if (!container) return;
        
        container.innerHTML = this.notifications.map(n => `
            <div class="notification notification-${n.type}" style="animation: slideIn 0.3s ease;">
                <span>${this.getNotificationIcon(n.type)} ${n.message}</span>
                <button onclick="DashboardState.removeNotification(${n.id})" style="background: none; border: none; cursor: pointer; margin-left: 10px;">
                    ✕
                </button>
            </div>
        `).join('');
    },
    
    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    },
    
    // ============================================================
    // 视图模式切换
    // ============================================================
    initViewToggle() {
        // 创建视图切换按钮
        const container = document.createElement('div');
        container.id = 'viewModeToggle';
        container.innerHTML = `
            <button class="btn btn-small btn-secondary" data-view="table" title="表格视图">
                📊
            </button>
            <button class="btn btn-small btn-secondary" data-view="card" title="卡片视图">
                🃏
            </button>
            <button class="btn btn-small btn-secondary" data-view="list" title="列表视图">
                📋
            </button>
            <button class="btn btn-small btn-secondary" id="themeToggleBtn" title="切换主题">
                🌙
            </button>
        `;
        
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            display: flex;
            gap: 8px;
            background: white;
            padding: 8px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        `;
        
        document.body.appendChild(container);
        
        // 绑定事件
        container.querySelectorAll('[data-view]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchViewMode(btn.dataset.view);
            });
        });
        
        document.getElementById('themeToggleBtn').addEventListener('click', () => {
            this.toggleTheme();
        });
    },
    
    switchViewMode(mode) {
        this.viewMode = mode;
        const table = document.getElementById('vulnTable')?.closest('.vulnerabilities-section');
        if (!table) return;
        
        table.classList.remove('view-table', 'view-card', 'view-list');
        table.classList.add(`view-${mode}`);
        
        // 更新按钮样式
        document.querySelectorAll('#viewModeToggle [data-view]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === mode);
        });
    },
    
    // ============================================================
    // 模态框系统
    // ============================================================
    showModal(content) {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = content;
        document.body.appendChild(modal);
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModals();
            }
        });
    },
    
    closeModals() {
        document.querySelectorAll('.modal.active').forEach(m => m.remove());
    },
    
    showSearchModal() {
        const html = `
            <div class="modal">
                <div class="modal-content">
                    <h3>🔍 快速搜索</h3>
                    <input type="text" 
                           placeholder="搜索 CVE、组件、描述..." 
                           style="width: 100%; padding: 12px; margin: 15px 0; border: 2px solid #ddd; border-radius: 8px; font-size: 1em;"
                           autofocus
                           onkeyup="if(event.key==='Enter'){DashboardState.search(this.value)}">
                    <div id="searchResults" style="max-height: 400px; overflow-y: auto;"></div>
                </div>
            </div>
        `;
        this.showModal(html);
        
        // 自动聚焦输入框
        setTimeout(() => {
            document.querySelector('#searchResults + input')?.focus();
        }, 100);
    },
    
    search(query) {
        if (!query.trim()) return;
        
        // 在实际应用中，这里会调用 API 进行搜索
        const results = scanData?.vulnerabilities?.filter(v => 
            v.cve_id.toLowerCase().includes(query.toLowerCase()) ||
            v.component.toLowerCase().includes(query.toLowerCase()) ||
            (v.description && v.description.toLowerCase().includes(query.toLowerCase()))
        ) || [];
        
        const resultsDiv = document.getElementById('searchResults');
        if (resultsDiv) {
            if (results.length === 0) {
                resultsDiv.innerHTML = '<p style="text-align: center; color: #999;">无搜索结果</p>';
            } else {
                resultsDiv.innerHTML = results.slice(0, 10).map(v => `
                    <div class="search-result-item" style="padding: 10px; margin: 5px 0; background: #f5f5f5; border-radius: 4px; cursor: pointer;"
                         onclick="window.location.href='/?scan=${v.firmware_id}'">
                        <strong>${v.cve_id}</strong> - ${v.component} ${v.version}
                        <br><small>${v.severity.toUpperCase()}</small>
                    </div>
                `).join('');
            }
        }
    },
    
    // ============================================================
    // 导出功能增强
    // ============================================================
    exportReport(format) {
        this.showToast(`正在生成${format === 'pdf' ? 'PDF' : 'Excel'}报告...`, 'info');
        
        const taskId = currentScanId;
        if (!taskId) {
            this.showToast('暂无扫描数据可导出', 'error');
            return;
        }
        
        const url = format === 'pdf' 
            ? `/api/report/pdf?firmware_id=${taskId}`
            : `/api/report/excel?firmware_id=${taskId}`;
        
        window.open(url, '_blank');
        
        this.showToast(`${format.toUpperCase()} 导出成功！`, 'success');
    },
    
    // ============================================================
    // 辅助功能
    // ============================================================
    toggleFilterPanel() {
        const panel = document.querySelector('.filter-panel');
        if (panel) {
            panel.classList.toggle('expanded');
        }
    },
    
    showHelpModal() {
        this.showKeyboardHelp();
    },
    
    // ============================================================
    // 动画效果
    // ============================================================
    animateValue(element, start, end, duration = 1000) {
        if (!element) return;
        
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            element.textContent = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        
        window.requestAnimationFrame(step);
    },
    
    fadeIn(element, duration = 300) {
        if (!element) return;
        element.style.opacity = '0';
        element.style.transition = `opacity ${duration}ms ease-out`;
        
        setTimeout(() => {
            element.style.opacity = '1';
        }, 10);
    },
    
    slideIn(element, direction = 'top') {
        if (!element) return;
        
        const transforms = {
            top: 'translateY(-20px)',
            bottom: 'translateY(20px)',
            left: 'translateX(-20px)',
            right: 'translateX(20px)'
        };
        
        element.style.transform = transforms[direction];
        element.style.opacity = '0';
        element.style.transition = 'all 0.3s ease-out';
        
        setTimeout(() => {
            element.style.transform = 'translate(0)';
            element.style.opacity = '1';
        }, 10);
    }
};

// 初始化增强模块
document.addEventListener('DOMContentLoaded', () => {
    DashboardState.init();
});

// 添加 CSS 动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    .notification-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
    }
    
    .notification {
        background: white;
        padding: 15px 20px;
        margin-bottom: 10px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        justify-content: space-between;
        animation: slideIn 0.3s ease;
    }
    
    .notification-success { border-left: 4px solid #28a745; }
    .notification-error { border-left: 4px solid #dc3545; }
    .notification-warning { border-left: 4px solid #ffc107; }
    .notification-info { border-left: 4px solid #17a2b8; }
    
    .modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9998;
        animation: fadeIn 0.3s ease;
    }
    
    .modal-content {
        background: white;
        padding: 30px;
        border-radius: 12px;
        max-width: 600px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    
    [data-theme="dark"] body {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e0e0e0;
    }
    
    [data-theme="dark"] section,
    [data-theme="dark"] .modal-content,
    [data-theme="dark"] .stat-card {
        background: #2d2d44;
        color: #e0e0e0;
    }
    
    [data-theme="dark"] table {
        background: #2d2d44;
    }
    
    [data-theme="dark"] input,
    [data-theme="dark"] select {
        background: #3d3d5c;
        color: #e0e0e0;
        border-color: #4d4d6c;
    }
    
    /* 视图模式 */
    .view-card .vulnTable,
    .view-card .table-responsive {
        display: none;
    }
    
    .view-card #vulnTableBody {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
    }
    
    .view-card #vulnTableBody tr {
        display: block;
        background: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .view-list .vulnTable th,
    .view-list .vulnTable td {
        padding: 8px 12px;
    }
`;
document.head.appendChild(style);

// 导出到全局
window.DashboardState = DashboardState;
