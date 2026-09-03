/**
 * 固件漏洞扫描平台 - 前端逻辑（v2.3 - Socket.IO 实时增强版）
 * 支持批量扫描、任务队列监控、高级图表和筛选、WebSocket 实时更新
 */

// Socket.IO 全局管理器（由 socketio-client.js 提供，直接使用 window.socketIOManager）

// ============================================================
// 全局状态
// ============================================================
let currentScanId = null;
let scanData = null;
let batchTasks = [];
let refreshInterval = null;
let scanHistory = []; // 扫描历史数据
let currentFilters = {
    timeRange: '7',
    severity: 'all',
    type: 'all'
};

// ============================================================
// DOM 元素（在 DOMContentLoaded 中初始化）
// ============================================================
let singleScanForm, batchScanForm, uploadProgress, statsGrid, vulnTableBody;
let severityFilter, batchFileInput, batchFileList, taskStatusSection;

function initDOMElements() {
    singleScanForm = document.getElementById('singleScanForm');
    batchScanForm = document.getElementById('batchScanForm');
    uploadProgress = document.getElementById('uploadProgress');
    statsGrid = document.getElementById('statsGrid');
    vulnTableBody = document.getElementById('vulnTableBody');
    severityFilter = document.getElementById('severityFilter');
    batchFileInput = document.getElementById('batchFileInput');
    batchFileList = document.getElementById('batchFileList');
    taskStatusSection = document.getElementById('taskStatusSection');
    
    // 检查关键元素是否存在
    if (!singleScanForm || !batchScanForm || !uploadProgress) {
        console.error('❌ 关键 DOM 元素未找到，页面可能未完全加载');
    }
}

// ============================================================
// Socket.IO 事件监听器
// ============================================================
function initSocketIOListeners() {
    // 从 window 获取 socketIOManager（由 socketio-client.js 提供）
    const socketIOManager = window.socketIOManager;
    
    if (!socketIOManager) {
        console.warn('⚠️ Socket.IO Manager 未初始化');
        return;
    }
    
    // 当收到进度更新时，刷新任务列表
    socketIOManager.on('onProgressUpdate', (data) => {
        console.log('📨 收到进度更新:', data);
        
        // 如果有当前扫描 ID，更新进度条显示
        if (currentScanId && data.task_id === currentScanId) {
            const progressText = document.getElementById('progressText');
            if (progressText) {
                progressText.textContent = `正在扫描... ${data.progress}% - ${data.stage}: ${data.details || ''}`;
            }
            
            // 如果进度超过 80%，自动检查是否完成
            if (data.progress >= 100) {
                setTimeout(() => {
                    refreshQueueStats();
                    loadScanHistory();
                }, 500);
            }
        }
    });
    
    // 当任务完成时，刷新 UI
    socketIOManager.on('onStatusChange', (data) => {
        if (data.status === 'completed') {
            console.log('✅ 任务完成，刷新界面');
            
            // 刷新队列统计
            setTimeout(() => {
                refreshQueueStats();
                loadScanHistory();
                
                // 如果有 Toast 显示功能，弹出通知
                if (window.DashboardState) {
                    DashboardState.showToast('✨ 扫描任务已完成！查看结果页...', 'success');
                }
            }, 1000);
        }
    });
    
    // 当连接状态变化时
    socketIOManager.on('onConnected', () => {
        console.log('🟢 Socket.IO 已连接');
    });
    
    socketIOManager.on('onDisconnected', () => {
        console.log('🔴 Socket.IO 已断开，回退到轮询模式');
    });
}

// ============================================================
// 初始化
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initDOMElements(); // 初始化 DOM 元素
    initEventListeners();
    initSocketIOListeners(); // 初始化 Socket.IO 监听器
    injectVersion(); // 从后端自动注入版本号（Phase 6）
    refreshQueueStats();
    loadScanHistory(); // 加载扫描历史
    
    // 每 10 秒自动刷新队列状态（作为 WebSocket 的备份）
    refreshInterval = setInterval(() => {
        refreshQueueStats();
        loadScanHistory(); // 定期更新历史记录
    }, 10000);
    
    // 检查 URL 参数中的 task ID
    const urlParams = new URLSearchParams(window.location.search);
    const taskId = urlParams.get('task');
    if (taskId) {
        loadTaskResult(taskId);
    }
});

function initEventListeners() {
    singleScanForm?.addEventListener('submit', handleSingleScan);
    batchScanForm?.addEventListener('submit', handleBatchScan);
    
    // 筛选控件事件
    document.getElementById('timeRangeFilter')?.addEventListener('change', (e) => {
        currentFilters.timeRange = e.target.value;
    });
    document.getElementById('typeFilter')?.addEventListener('change', (e) => {
        currentFilters.type = e.target.value;
    });
    
    severityFilter?.addEventListener('change', filterVulnerabilities);
    
    // 批量文件选择监听
    if (batchFileInput) {
        batchFileInput.addEventListener('change', handleBatchFileSelect);
    }
}

// ============================================================
// Phase 6: 版本号自动注入
// ============================================================
/**
 * 从后端 /api/health 获取版本号并注入到页面，避免版本号硬编码滞后
 */
async function injectVersion() {
    try {
        const resp = await fetch('/api/health', { cache: 'no-store' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        const version = data.version || 'v2.6.0';
        const appVersionEl = document.getElementById('app-version');
        const footerVersionEl = document.getElementById('footer-version');
        const titleEl = document.querySelector('title');
        if (appVersionEl) appVersionEl.textContent = version;
        if (footerVersionEl) footerVersionEl.textContent = version;
        if (titleEl && !titleEl.textContent.includes(version)) {
            titleEl.textContent = `🐢 玄武·AFVS - 汽车固件漏洞扫描器 ${version}`;
        }
        console.log(`✅ 版本号已注入: ${version}`);
    } catch (err) {
        console.warn('⚠️ 版本号注入失败，使用默认值:', err);
        // 失败时保留 HTML 中的默认值（v2.6.0）
    }
}

// ============================================================
// 单个文件扫描
// ============================================================
async function handleSingleScan(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('firmwareFile');
    const firmwareType = document.getElementById('firmwareType').value;
    const file = fileInput.files[0];
    
    if (!file) {
        alert('请选择文件');
        return;
    }
    
    showProgress(true, '正在上传并扫描...');
    
    try {
        // 1. 上传文件
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const uploadResult = await uploadResponse.json();
        
        if (!uploadResult.success) {
            throw new Error(uploadResult.message);
        }
        
        const firmwareId = uploadResult.filename;  // 保存 firmware_id
        
        // 2. 开始扫描
        const scanFormData = new FormData();
        scanFormData.append('firmware_id', firmwareId);
        scanFormData.append('firmware_type', firmwareType);
        
        showProgress(true, '正在扫描中...');
        
        const scanResponse = await fetch('/api/scan', {
            method: 'POST',
            body: scanFormData
        });
        
        const scanResult = await scanResponse.json();
        
        if (!scanResult.success) {
            throw new Error(scanResult.detail || '扫描失败');
        }
        
        // 使用 task_id（UUID）进行后续操作
        const taskId = scanResult.task_id;
        currentScanId = taskId;
        
        // 3. 订阅 WebSocket 实时更新（如果可用）
        if (typeof subscribeToTaskSO === 'function') {
            subscribeToTaskSO(taskId);
            console.log(`📝 已订阅任务：${taskId}`);
        }
        
        // 4. 显示成功提示并开始轮询任务状态
        showNotification('✅ 文件上传成功，扫描任务已提交！', 'success');
        showProgress(true, '正在扫描中...');
        
        // 5. 轮询任务状态直到完成（使用 task_id）
        pollTaskStatus(taskId);
        
    } catch (error) {
        console.error('扫描失败:', error);
        showNotification(`❌ 扫描失败：${error.message}`, 'error');
        alert(`扫描失败：${error.message}`);
    } finally {
        // 不立即隐藏进度条，等待任务完成
    }
}

// ============================================================
// 任务状态轮询（备用方案，当 WebSocket 不可用时）
// ============================================================
async function pollTaskStatus(taskId) {
    const maxAttempts = 60; // 最多轮询 60 次（约 1 分钟）
    let attempts = 0;
    
    const poll = async () => {
        try {
            const response = await fetch(`/api/task/${taskId}/status`);
            const task = await response.json();
            
            console.log(`📊 任务状态: ${task.status} (${task.progress || 0}%)`);
            
            // 更新进度显示
            if (task.progress !== undefined) {
                showProgress(true, `正在扫描... ${task.progress}% - ${task.status}`);
            } else {
                showProgress(true, `正在扫描... 状态：${task.status}`);
            }
            
            if (task.status === 'completed') {
                showProgress(false);
                showNotification('✅ 扫描完成！正在加载结果...', 'success');
                
                // 加载完整结果
                await loadTaskResult(taskId);
                refreshQueueStats();
                loadScanHistory();
                return;
            } else if (task.status === 'failed') {
                showProgress(false);
                showNotification(`❌ 扫描失败：${task.error_message || '未知错误'}`, 'error');
                alert(`扫描失败：${task.error_message || '未知错误'}`);
                return;
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 2000); // 2 秒后再次轮询
            } else {
                showProgress(false);
                showNotification('⏱️ 扫描超时，请手动刷新查看结果', 'warning');
            }
        } catch (error) {
            console.error('轮询任务状态失败:', error);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 2000);
            }
        }
    };
    
    poll();
}

// ============================================================
// 批量扫描
// ============================================================
function handleBatchFileSelect(event) {
    const files = event.target.files;
    
    if (!files || files.length === 0) {
        updateBatchFileCount(0);
        document.getElementById('batchSubmitBtn').disabled = true;
        return;
    }
    
    batchTasks = Array.from(files).map(file => ({
        name: file.name,
        type: document.getElementById('batchFirmwareType').value,
        file: file
    }));
    
    updateBatchFileCount(files.length);
    document.getElementById('batchSubmitBtn').disabled = false;
}

function updateBatchFileCount(count) {
    const countEl = document.getElementById('batchFileCount');
    if (count === 0) {
        countEl.textContent = '尚未选择文件';
    } else {
        countEl.innerHTML = `已选择 <strong>${count}</strong> 个文件`;
    }
}

async function handleBatchScan(e) {
    e.preventDefault();
    
    if (batchTasks.length === 0) {
        alert('请先选择文件');
        return;
    }
    
    showProgress(true, `正在提交 ${batchTasks.length} 个扫描任务...`);
    
    try {
        // 上传所有文件
        const uploadedFiles = [];
        
        for (const task of batchTasks) {
            const formData = new FormData();
            formData.append('file', task.file);
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                uploadedFiles.push({
                    path: result.path,
                    type: task.type,
                    filename: task.name
                });
            }
        }
        
        // 提交批量扫描任务
        const scanResponse = await fetch('/api/scan/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                files: uploadedFiles
            })
        });
        
        const scanResult = await scanResponse.json();
        
        if (!scanResult.success) {
            throw new Error(scanResult.detail || '批量扫描提交失败');
        }
        
        showProgress(true, `${scanResult.submitted} 个任务已提交到队列`);
        
        // 记录任务 ID
        batchTasks = scanResult.tasks.map(t => ({
            ...t,
            checked: false
        }));
        
        // 订阅所有任务的 WebSocket 实时更新
        if (typeof subscribeToTaskSO === 'function') {
            scanResult.tasks.forEach(task => {
                subscribeToTaskSO(task.task_id);
                console.log(`📝 批量扫描：已订阅任务 ${task.task_id}`);
            });
        }
        
        // 显示任务列表
        setTimeout(() => {
            showProgress(false);
            alert(`✅ 成功提交 ${scanResult.submitted} 个任务！\n\n请查看下方的"任务队列状态"监控进度。`);
            refreshQueueStats();
        }, 1000);
        
    } catch (error) {
        console.error('批量扫描失败:', error);
        alert(`批量扫描失败：${error.message}`);
        showProgress(false);
    }
}

// ============================================================
// 任务队列管理
// ============================================================
async function refreshQueueStats() {
    try {
        // 获取队列统计
        const statsResponse = await fetch('/api/queue/stats');
        const stats = await statsResponse.json();
        
        // 更新统计数字
        document.getElementById('queuedCount').textContent = stats.pending + stats.queued;
        document.getElementById('runningCount').textContent = stats.running;
        document.getElementById('completedCount').textContent = stats.completed;
        document.getElementById('failedCount').textContent = stats.failed;
        
        // 获取最新任务列表
        const tasksResponse = await fetch('/api/tasks?limit=10');
        const tasksData = await tasksResponse.json();
        
        // 如果有运行中的任务，显示实时状态
        if (stats.running > 0 || stats.queued > 0) {
            displayActiveTasks(tasksData.tasks);
        } else {
            hideActiveTasks();
        }
        
    } catch (error) {
        console.error('刷新队列状态失败:', error);
    }
}

function displayActiveTasks(tasks) {
    const section = document.getElementById('taskStatusSection');
    const container = document.getElementById('activeTasks');
    
    if (!section || !container) return;
    
    const activeTasks = tasks.filter(t => t.status !== 'completed' && t.status !== 'cancelled');
    
    if (activeTasks.length === 0) {
        hideActiveTasks();
        return;
    }
    
    section.classList.remove('hidden');
    
    container.innerHTML = activeTasks.map(task => `
        <div class="task-item ${task.status}" style="padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${task.filename}</strong>
                    <span class="status-badge status-${task.status}" style="margin-left: 8px;">
                        ${task.status.toUpperCase()}
                    </span>
                </div>
                <div style="text-align: right;">
                    ${task.status === 'running' ? `
                        <div style="width: 150px; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">
                            <div style="width: ${task.progress}%; height: 100%; background: #4CAF50; transition: width 0.3s;"></div>
                        </div>
                        <small>${task.progress}%</small>
                    ` : ''}
                </div>
            </div>
            ${task.started_at ? `<small style="color: #666;">开始：${formatTime(task.started_at)}</small>` : ''}
        </div>
    `).join('');
}

function hideActiveTasks() {
    const section = document.getElementById('taskStatusSection');
    if (section) {
        section.classList.add('hidden');
    }
}

function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString('zh-CN');
    } catch (e) {
        return isoString;
    }
}

async function cancelTask(taskId) {
    if (!confirm(`确定要取消任务 ${taskId} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/task/${taskId}/cancel`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('任务已取消');
            refreshQueueStats();
        } else {
            const error = await response.json();
            alert(`取消失败：${error.detail}`);
        }
    } catch (error) {
        alert(`取消失败：${error.message}`);
    }
}

async function downloadReport(taskId, format) {
    try {
        const response = await fetch(`/api/reports/${taskId}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${taskId}_report.yaml`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            const error = await response.json();
            alert(`下载失败：${error.detail}`);
        }
    } catch (error) {
        alert(`下载失败：${error.message}`);
    }
}

// ============================================================
// 结果显示
// ============================================================
async function loadTaskResult(taskId) {
    try {
        showProgress(true, '正在加载任务结果...');
        
        // 轮询直到任务完成
        while (true) {
            const response = await fetch(`/api/task/${taskId}/status`);
            const task = await response.json();
            
            if (task.status === 'completed') {
                // 获取完整结果
                const resultResponse = await fetch(`/api/task/${taskId}/result`);
                const result = await resultResponse.json();
                
                displayScanResult(result);
                showProgress(false);
                break;
            } else if (task.status === 'failed') {
                alert(`任务失败：${task.error_message}`);
                showProgress(false);
                break;
            }
            
            // 等待 1 秒后重试
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
    } catch (error) {
        console.error('加载任务结果失败:', error);
        alert(`加载失败：${error.message}`);
        showProgress(false);
    }
}

function displayScanResult(data) {
    scanData = data;
    
    // 更新统计数据
    document.getElementById('totalCves').textContent = data.total_cves;
    document.getElementById('criticalCount').textContent = data.critical_count;
    document.getElementById('highCount').textContent = data.high_count;
    document.getElementById('mediumCount').textContent = data.medium_count;
    document.getElementById('lowCount').textContent = data.low_count;
    
    // 显示不合规 CVE 数量（如果有）
    if (data.r155_compliance && data.r155_compliance.violating_cves !== undefined) {
        const r155CountEl = document.getElementById('r155Count');
        if (r155CountEl) {
            r155CountEl.textContent = data.r155_compliance.violating_cves;
        }
        
        // 调用 R155 UI 模块处理合规数据
        if (window.updateComplianceStats) {
            window.updateComplianceStats(data.r155_compliance);
            
            // 保存数据供选项卡使用
            window.currentComplianceData = data.r155_compliance;
            
            // 默认渲染违规表格（如果存在违规）
            if (data.r155_compliance.violations && data.r155_compliance.violations.length > 0) {
                if (window.renderViolationsTable) {
                    window.renderViolationsTable(data.r155_compliance.violations);
                }
                
                // 默认切换到合规选项卡
                setTimeout(() => {
                    if (window.switchTab) {
                        switchTab('compliance-details');
                    }
                }, 500);
            }
        }
    } else {
        // 隐藏 R155 相关组件
        showComplianceUI(false);
    }
    
    // 渲染表格
    renderVulnerabilityTable(data.vulnerabilities);
    
    // 渲染组件
    renderComponents(data.components);
    
    // 绘制图表
    drawSeverityChart(data);
    drawPriorityChart(data);
    
    // 显示组件区域
    document.getElementById('componentsSection').style.display = 'block';
}

// ============================================================
// 工具函数
// ============================================================
function showProgress(show, text = '正在处理...') {
    if (!uploadProgress) return;
    
    if (show) {
        uploadProgress.classList.remove('hidden');
        document.getElementById('progressText').textContent = text;
    } else {
        uploadProgress.classList.add('hidden');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderVulnerabilityTable(vulnerabilities) {
    if (!vulnerabilities || vulnerabilities.length === 0) {
        vulnTableBody.innerHTML = '<tr><td colspan="8" class="no-data">未发现漏洞或数据为空</td></tr>';
        return;
    }
    
    vulnTableBody.innerHTML = vulnerabilities.map(vuln => `
        <tr>
            <td><strong>${escapeHtml(vuln.cve_id)}</strong></td>
            <td>${escapeHtml(vuln.component)}</td>
            <td>${escapeHtml(vuln.version)}</td>
            <td><span class="severity-badge severity-${vuln.severity.toLowerCase()}">${vuln.severity}</span></td>
            <td>${vuln.cvss_score?.toFixed(1) || 'N/A'}</td>
            <td><strong>${vuln.priority_score?.toFixed(3) || 'N/A'}</strong></td>
            <td class="${vuln.r155_non_compliant ? 'compliance-no' : 'compliance-yes'}">
                ${vuln.r155_non_compliant ? '❌ 不合规' : '✅ 合规'}
            </td>
            <td>
                <button onclick="showDetail('${vuln.cve_id}')" class="btn btn-secondary" style="padding: 4px 12px; font-size: 0.9em;">详情</button>
            </td>
        </tr>
    `).join('');
}

function renderComponents(components) {
    const container = document.getElementById('componentsList');
    
    if (!components || components.length === 0) {
        container.innerHTML = '<p class="no-data">未识别到组件</p>';
        return;
    }
    
    container.innerHTML = components.map(comp => `
        <div class="component-card">
            <div class="component-name">${escapeHtml(comp.name)}</div>
            <div class="component-version">版本：${escapeHtml(comp.version)}</div>
            <div class="component-version">类型：${escapeHtml(comp.type)}</div>
        </div>
    `).join('');
}

function filterVulnerabilities() {
    const filterValue = severityFilter.value;
    
    if (!scanData || !scanData.vulnerabilities) return;
    
    let filtered = scanData.vulnerabilities;
    
    if (filterValue !== 'all') {
        filtered = scanData.vulnerabilities.filter(v => 
            v.severity.toLowerCase() === filterValue
        );
    }
    
    renderVulnerabilityTable(filtered);
}

function showDetail(cveId) {
    const vuln = scanData.vulnerabilities.find(v => v.cve_id === cveId);
    if (vuln) {
        alert(`${vuln.cve_id}\n\n描述:\n${vuln.description}\n\nCVSS: ${vuln.cvss_score}\n优先级: ${vuln.priority_score?.toFixed(3)}\nR155 合规: ${vuln.r155_non_compliant ? '不合规' : '合规'}`);
    }
}

// Canvas 图表绘制（保持原有实现）
function drawSeverityChart(data) {
    const canvas = document.getElementById('severityChart');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    ctx.clearRect(0, 0, width, height);
    
    const counts = {
        critical: data.critical_count,
        high: data.high_count,
        medium: data.medium_count,
        low: data.low_count
    };
    
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    
    if (total === 0) {
        drawNoDataText(ctx, width, height, '暂无漏洞数据');
        return;
    }
    
    const centerX = width / 2;
    const centerY = height / 2 + 20;
    const radius = Math.min(width, height) / 2.5;
    
    const colors = {
        critical: '#dc3545',
        high: '#fd7e14',
        medium: '#ffc107',
        low: '#28a745'
    };
    
    const labels = ['严重', '高危', '中危', '低危'];
    const keys = ['critical', 'high', 'medium', 'low'];
    
    let startAngle = -Math.PI / 2;
    
    keys.forEach((key, index) => {
        const sliceAngle = (counts[key] / total) * 2 * Math.PI;
        
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
        ctx.closePath();
        ctx.fillStyle = colors[key];
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        startAngle += sliceAngle;
    });
    
    const legendX = width - 120;
    const legendY = 40;
    
    keys.forEach((key, index) => {
        ctx.fillStyle = colors[key];
        ctx.fillRect(legendX, legendY + index * 25, 15, 15);
        
        ctx.fillStyle = '#333';
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        ctx.fillText(`${labels[index]}: ${counts[key]}`, legendX + 20, legendY + index * 25 + 12);
    });
    
    ctx.fillStyle = '#333';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('严重程度分布', centerX, 25);
}

function drawPriorityChart(data) {
    const canvas = document.getElementById('priorityChart');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    ctx.clearRect(0, 0, width, height);
    
    const vulns = data.vulnerabilities || [];
    
    if (vulns.length === 0) {
        drawNoDataText(ctx, width, height, '暂无漏洞数据');
        return;
    }
    
    const topVulns = vulns.slice(0, 10);
    
    const padding = { top: 40, right: 30, bottom: 60, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    const barWidth = chartWidth / topVulns.length - 10;
    const maxPriority = Math.max(...topVulns.map(v => v.priority_score));
    
    ctx.strokeStyle = '#ccc';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, height - padding.bottom);
    ctx.lineTo(width - padding.right, height - padding.bottom);
    ctx.stroke();
    
    topVulns.forEach((vuln, index) => {
        const x = padding.left + 10 + index * (barWidth + 10);
        const barHeight = (vuln.priority_score / maxPriority) * chartHeight;
        const y = height - padding.bottom - barHeight;
        
        const gradient = ctx.createLinearGradient(x, y, x, height - padding.bottom);
        gradient.addColorStop(0, '#667eea');
        gradient.addColorStop(1, '#764ba2');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth, barHeight);
        
        ctx.fillStyle = '#333';
        ctx.font = '10px Arial';
        ctx.textAlign = 'center';
        
        const shortId = vuln.cve_id.length > 12 ? vuln.cve_id.substring(0, 10) + '..' : vuln.cve_id;
        ctx.fillText(shortId, x + barWidth / 2, height - padding.bottom + 15);
        
        ctx.fillStyle = '#666';
        ctx.font = '11px Arial';
        ctx.fillText(vuln.priority_score.toFixed(3), x + barWidth / 2, y - 5);
    });
    
    ctx.save();
    ctx.translate(15, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('优先级分数', 0, 0);
    ctx.restore();
    
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('CVE ID', width / 2, height - 10);
    
    ctx.fillStyle = '#333';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Top 10 高优先级漏洞', width / 2, 25);
}

function drawNoDataText(ctx, width, height, text) {
    ctx.fillStyle = '#999';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(text, width / 2, height / 2);
}

// PDF 和 Excel 导出按钮事件
document.getElementById('exportPdfBtn')?.addEventListener('click', async () => {
    if (!currentScanId) {
        alert('请先进行扫描');
        return;
    }
    
    const btn = document.getElementById('exportPdfBtn');
    const originalText = btn.textContent;
    btn.textContent = '⏳ 生成中...';
    btn.disabled = true;
    
    try {
        // 首先尝试调用服务器端 API
        const formData = new FormData();
        formData.append('firmware_id', currentScanId);
        
        const response = await fetch('/api/report/pdf', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // 服务器端 PDF 成功
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `xuanwu_scan_report_${currentScanId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            alert('✅ PDF 报告已生成并开始下载！');
        } else {
            // 服务器端失败，使用客户端生成作为备用方案
            console.log('服务器端 PDF 不可用，使用客户端生成');
            await generateClientSidePDF(currentScanId);
        }
    } catch (error) {
        console.error('PDF 生成错误:', error);
        // 如果服务器端失败，尝试客户端生成
        try {
            await generateClientSidePDF(currentScanId);
        } catch (clientError) {
            alert(`❌ PDF 生成失败：${error.message}`);
        }
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
});

/**
 * 客户端 PDF 生成功能（使用 jsPDF + html2canvas）
 */
async function generateClientSidePDF(scanId) {
    if (!window.jspdf || !window.html2canvas) {
        alert('❌ PDF 生成库未加载，请稍后重试');
        return;
    }
    
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('p', 'mm', 'a4');
    
    try {
        alert('📄 正在生成客户端 PDF 报告，请稍候...');
        
        // 获取需要导出的区域
        const dashboardSection = document.querySelector('.dashboard-section');
        const vulnerabilitiesSection = document.querySelector('.vulnerabilities-section');
        
        if (!dashboardSection || !vulnerabilitiesSection) {
            throw new Error('找不到要导出的内容');
        }
        
        // 创建临时的导出容器
        const exportContainer = document.createElement('div');
        exportContainer.style.cssText = `
            position: fixed;
            left: -9999px;
            top: 0;
            width: 210mm; /* A4 宽度 */
            background: white;
            padding: 20px;
            font-family: Arial, sans-serif;
        `;
        
        // 复制内容到临时容器
        exportContainer.innerHTML = `
            <h1 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">玄武固件安全扫描报告</h1>
            <p style="text-align: center; color: #7f8c8d; margin-bottom: 30px;">扫描时间：${new Date().toLocaleString('zh-CN')}</p>
            ${dashboardSection.innerHTML}
            ${vulnerabilitiesSection.innerHTML}
        `;
        
        document.body.appendChild(exportContainer);
        
        // 使用 html2canvas 截图
        const canvas = await html2canvas(exportContainer, {
            scale: 2, // 提高清晰度
            useCORS: true,
            logging: false
        });
        
        // 移除临时容器
        document.body.removeChild(exportContainer);
        
        // 将 canvas 添加到 PDF
        const imgData = canvas.toDataURL('image/png');
        const imgWidth = 210 - 20; // A4 宽度减去边距
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        
        doc.setFontSize(16);
        doc.setTextColor(44, 62, 80);
        doc.text('玄武固件安全扫描报告', 105, 15, { align: 'center' });
        
        doc.setFontSize(10);
        doc.setTextColor(127, 140, 141);
        doc.text(`扫描时间：${new Date().toLocaleString('zh-CN')}`, 105, 25, { align: 'center' });
        
        doc.addImage(imgData, 'PNG', 10, 35, imgWidth, imgHeight);
        
        // 保存 PDF
        doc.save(`xuanwu_scan_report_${scanId}.pdf`);
        
        alert('✅ PDF 报告已成功生成并下载！');
        
    } catch (error) {
        console.error('客户端 PDF 生成错误:', error);
        throw error;
    }
}

document.getElementById('exportExcelBtn')?.addEventListener('click', async () => {
    if (!currentScanId) {
        alert('请先进行扫描');
        return;
    }
    
    const btn = document.getElementById('exportExcelBtn');
    const originalText = btn.textContent;
    btn.textContent = '⏳ 生成中...';
    btn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('firmware_id', currentScanId);
        
        const response = await fetch('/api/report/excel', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `xuanwu_scan_report_${currentScanId}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            alert('✅ Excel 报告已生成并开始下载！');
        } else {
            alert('❌ Excel 生成失败');
        }
    } catch (error) {
        console.error('Excel 生成错误:', error);
        alert(`❌ Excel 生成失败：${error.message}`);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
});

// ============================================================
// 新增功能：筛选和导出（v2.2）
// ============================================================

async function loadScanHistory() {
    try {
        const response = await fetch('/api/tasks?limit=50&status=completed');
        const data = await response.json();
        
        scanHistory = data.tasks.map(task => ({
            id: task.task_id,
            filename: task.filename,
            type: task.firmware_type || 'bin',
            created_at: task.created_at,
            result: task.result
        })).filter(t => t.result); // 只保留有结果的
        
        renderHistoryTable();
        updateTrendChart();
    } catch (error) {
        console.error('加载扫描历史失败:', error);
    }
}

function renderHistoryTable() {
    const tbody = document.getElementById('historyTableBody');
    
    if (!scanHistory || scanHistory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-data">暂无扫描历史</td></tr>';
        return;
    }
    
    tbody.innerHTML = scanHistory.slice(0, 20).map(scan => {
        const r = scan.result;
        const date = new Date(scan.created_at).toLocaleDateString('zh-CN');
        
        return `
            <tr>
                <td>${date}</td>
                <td style="font-family: monospace; font-size: 0.9em;">${scan.id.substring(0, 8)}...</td>
                <td>${escapeHtml(scan.filename)}</td>
                <td><span class="badge">${scan.type}</span></td>
                <td><strong>${r.total_cves || 0}</strong></td>
                <td class="${r.critical_count > 0 ? 'text-danger' : ''}">${r.critical_count || 0}</td>
                <td class="${r.high_count > 0 ? 'text-warning' : ''}">${r.high_count || 0}</td>
                <td class="${r.r155_non_compliant > 0 ? 'compliance-no' : 'compliance-yes'}">
                    ${r.r155_non_compliant || 0}
                </td>
                <td>
                    <button onclick="viewResult('${scan.id}')" class="btn btn-small btn-primary">查看</button>
                    <button onclick="downloadYamlReport('${scan.id}')" class="btn btn-small btn-secondary">YAML</button>
                </td>
            </tr>
        `;
    }).join('');
}

function viewResult(scanId) {
    window.location.href = `/?task=${scanId}`;
}

function downloadYamlReport(scanId) {
    window.open(`/api/reports/${scanId}`, '_blank');
}

async function applyFilters() {
    currentFilters.severity = document.getElementById('severityFilter').value;
    
    if (scanData && scanData.vulnerabilities) {
        filterVulnerabilities();
    }
    
    alert('筛选已应用！');
}

function resetFilters() {
    document.getElementById('timeRangeFilter').value = '7';
    document.getElementById('severityFilter').value = 'all';
    document.getElementById('typeFilter').value = 'all';
    
    currentFilters = {
        timeRange: '7',
        severity: 'all',
        type: 'all'
    };
    
    if (scanData && scanData.vulnerabilities) {
        filterVulnerabilities();
    }
    
    loadScanHistory();
}

function filterVulnerabilities() {
    const filterValue = severityFilter.value;
    
    if (!scanData || !scanData.vulnerabilities) return;
    
    let filtered = scanData.vulnerabilities;
    
    if (filterValue !== 'all') {
        filtered = scanData.vulnerabilities.filter(v => 
            v.severity.toLowerCase() === filterValue
        );
    }
    
    renderVulnerabilityTable(filtered);
}

async function exportExcel() {
    if (!scanData) {
        alert('暂无扫描数据，请先扫描固件');
        return;
    }
    
    // 调用后端 API 生成 Excel
    try {
        const formData = new FormData();
        formData.append('firmware_id', currentScanId);
        
        const response = await fetch('/api/report/excel', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentScanId}_report.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showNotification('✅ Excel 报告已下载', 'success');
        } else {
            const error = await response.json();
            alert(`导出失败：${error.detail}`);
        }
    } catch (error) {
        alert(`导出失败：${error.message}`);
    }
}

async function exportPDF() {
    if (!scanData) {
        alert('暂无扫描数据，请先扫描固件');
        return;
    }
    
    // 简单的 PDF 生成（使用浏览器打印功能）
    try {
        // 打开新窗口打印
        const printWindow = window.open('', '_blank');
        
        // 构建 HTML
        let html = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>固件漏洞扫描报告 - ${currentScanId}</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    h1 { color: #333; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background: #667eea; color: white; }
                    .critical { color: #dc3545; }
                    .high { color: #fd7e14; }
                    .summary { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 8px; }
                </style>
            </head>
            <body>
                <h1>🐢 固件漏洞扫描报告</h1>
                <p><strong>扫描 ID:</strong> ${currentScanId}</p>
                <p><strong>扫描时间:</strong> ${new Date().toLocaleString('zh-CN')}</p>
                
                <div class="summary">
                    <h3>统计摘要</h3>
                    <p><strong>总漏洞数:</strong> ${scanData.total_cves}</p>
                    <p><strong>严重:</strong> <span class="critical">${scanData.critical_count}</span></p>
                    <p><strong>高危:</strong> <span class="high">${scanData.high_count}</span></p>
                    <p><strong>R155 不合规:</strong> ${scanData.r155_non_compliant || 0}</p>
                </div>
                
                <h3>漏洞列表</h3>
                <table>
                    <thead>
                        <tr>
                            <th>CVE ID</th>
                            <th>组件</th>
                            <th>版本</th>
                            <th>严重程度</th>
                            <th>CVSS</th>
                            <th>优先级</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        scanData.vulnerabilities.forEach(v => {
            html += `
                <tr>
                    <td><strong>${v.cve_id}</strong></td>
                    <td>${v.component}</td>
                    <td>${v.version}</td>
                    <td class="${v.severity.toLowerCase()}">${v.severity}</td>
                    <td>${v.cvss_score}</td>
                    <td>${v.priority_score?.toFixed(3)}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
                
                <script>
                    setTimeout(() => {
                        window.print();
                        window.close();
                    }, 500);
                </script>
            </body>
            </html>
        `;
        
        printWindow.document.write(html);
        printWindow.document.close();
        
        showNotification('📄 PDF 报告准备就绪，请点击保存', 'info');
    } catch (error) {
        alert(`导出失败：${error.message}`);
    }
}

function updateTrendChart() {
    // 准备趋势数据（最近 7 天）
    const last7Days = scanHistory.slice(0, 7).reverse();
    
    const trendData = last7Days.map(scan => {
        const date = new Date(scan.created_at);
        return {
            date: date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
            total_cves: scan.result.total_cves || 0,
            critical_count: scan.result.critical_count || 0
        };
    });
    
    if (window.charts && window.charts.trendLine) {
        window.charts.trendLine.render(trendData);
    }
}

function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'};
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 添加动画 CSS（使用立即执行函数避免全局变量冲突）
(function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        .text-danger { color: #dc3545; font-weight: bold; }
        .text-warning { color: #fd7e14; font-weight: bold; }
    `;
    document.head.appendChild(style);
})();
