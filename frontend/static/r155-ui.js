/**
 * R155 合规报告前端交互逻辑
 * 
 * 功能:
 * - 合规评分显示
 * - 选项卡切换
 * - 违规详情表格填充
 * - 类别得分可视化
 * - 修复建议展示
 */

// 全局状态
let currentComplianceData = null;

// ============================================================
// 核心函数
// ============================================================

/**
 * 显示/隐藏 R155 合规相关组件
 */
function showComplianceUI(show) {
    const complianceCard = document.getElementById('complianceCard');
    const complianceTabs = document.getElementById('r155TabsSection');
    
    if (show) {
        if (complianceCard) complianceCard.style.display = 'block';
        if (complianceTabs) complianceTabs.style.display = 'block';
        // 也可以显示雷达图部分
        const radarSection = document.getElementById('complianceRadarSection');
        if (radarSection) radarSection.style.display = 'block';
    } else {
        if (complianceCard) complianceCard.style.display = 'none';
        if (complianceTabs) complianceTabs.style.display = 'none';
        const radarSection = document.getElementById('complianceRadarSection');
        if (radarSection) radarSection.style.display = 'none';
    }
}

/**
 * 更新 R155 合规统计卡片
 * @param {Object} compliance - 合规报告对象
 */
function updateComplianceStats(compliance) {
    const scoreElement = document.getElementById('complianceScore');
    const statusElement = document.getElementById('complianceStatus') || document.getElementById('complianceLevel');
    const countElement = document.getElementById('r155Count');
    
    if (!scoreElement) return;
    
    // 更新分数
    const score = compliance.compliance_score || 100;
    scoreElement.textContent = `${score.toFixed(1)}/100`;
    
    // 根据分数设置等级和颜色
    let levelText = '';
    let bgColor = '';
    
    if (score >= 90) {
        levelText = '✅ 优秀';
        bgColor = 'linear-gradient(135deg, #10b981 0%, #34d399 100%)';
    } else if (score >= 75) {
        levelText = '⚠️ 良好';
        bgColor = 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)';
    } else if (score >= 60) {
        levelText = '⚠️ 中等';
        bgColor = 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)';
    } else {
        levelText = '❌ 需改进';
        bgColor = 'linear-gradient(135deg, #ef4444 0%, #f87171 100%)';
    }
    
    if (statusElement) {
        statusElement.textContent = levelText;
    }
    
    // 更新卡片背景色
    const card = scoreElement.closest('.stat-card');
    if (card) {
        card.style.background = bgColor;
        card.style.color = 'white';
    }
    
    // 显示不合规 CVE 数量
    if (countElement && compliance.violating_cves !== undefined) {
        countElement.textContent = compliance.violating_cves;
    }
    
    // 显示总违规数
    if (compliance.violations && compliance.violations.length > 0) {
        showComplianceUI(true);
    }
}

/**
 * 切换合规报告选项卡
 * @param {string} tabId - 要切换到的选项卡 ID
 */
function switchTab(tabId) {
    // 获取所有按钮和内容区域
    const buttons = document.querySelectorAll('#r155TabsSection .tab-btn');
    const panes = document.querySelectorAll('#r155TabsSection .tab-pane');
    
    // 移除所有激活状态
    buttons.forEach(btn => btn.classList.remove('active'));
    panes.forEach(pane => pane.classList.remove('active'));
    
    // 激活当前选中的
    const activeButton = document.querySelector(`#r155TabsSection .tab-btn[onclick="switchTab('${tabId}')"]`);
    const activePane = document.getElementById(tabId);
    
    if (activeButton) activeButton.classList.add('active');
    if (activePane) activePane.classList.add('active');
    
    // 渲染对应内容
    if (tabId === 'compliance-details' && currentComplianceData) {
        renderViolationsTable(currentComplianceData.violations);
    } else if (tabId === 'compliance-categories' && currentComplianceData) {
        renderCategoryChart(currentComplianceData.category_scores);
    } else if (tabId === 'compliance-recommendations' && currentComplianceData) {
        renderRecommendations(currentComplianceData.recommendations);
    }
}

// ============================================================
// 数据渲染函数
// ============================================================

/**
 * 渲染违规详情表格
 * @param {Array} violations - 违规列表
 */
function renderViolationsTable(violations) {
    const tbody = document.getElementById('violationsBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!violations || violations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">🎉 没有发现 R155 合规问题！</td></tr>';
        return;
    }
    
    violations.forEach(violation => {
        const row = document.createElement('tr');
        
        // 根据扣分设置严重性标记
        let severityBadge = '';
        if (violation.penalty_score > 5) {
            severityBadge = '<span style="color: #ef4444;">●</span>';
        } else if (violation.penalty_score > 3) {
            severityBadge = '<span style="color: #f59e0b;">●</span>';
        } else {
            severityBadge = '<span style="color: #10b981;">●</span>';
        }
        
        row.innerHTML = `
            <td>${severityBadge} ${violation.rule_id}</td>
            <td><strong>${violation.cve_id}</strong></td>
            <td>${violation.component}</td>
            <td style="font-weight: bold; color: #ef4444;">${violation.penalty_score.toFixed(2)}</td>
            <td>${violation.remediation}</td>
        `;
        
        tbody.appendChild(row);
    });
}

/**
 * 渲染类别得分图表（使用 Chart.js）
 * @param {Object} categoryScores - 类别得分对象
 */
function renderCategoryChart(categoryScores) {
    const canvas = document.getElementById('categoryPieChart');
    if (!canvas || !categoryScores) return;
    
    try {
        // 清除旧图表
        const ctx = canvas.getContext('2d');
        
        // 准备数据
        const labels = Object.keys(categoryScores);
        const data = Object.values(categoryScores);
        const colors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
            '#8b5cf6', '#ec4899', '#06b6d4'
        ];
        
        // 创建饼图
        if (window.categoryPieChartInstance) {
            window.categoryPieChartInstance.destroy();
        }
        
        window.categoryPieChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'R155 合规类别得分分布',
                        font: { size: 16 }
                    },
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
        
        // 同时渲染雷达图
        renderCategoryRadar(categoryScores);
        
    } catch (error) {
        console.error('渲染类别图表失败:', error);
    }
}

/**
 * 渲染雷达图
 * @param {Object} categoryScores - 类别得分对象
 */
function renderCategoryRadar(categoryScores) {
    const canvas = document.getElementById('complianceRadar');
    if (!canvas || !categoryScores) return;
    
    try {
        const ctx = canvas.getContext('2d');
        
        if (window.complianceRadarInstance) {
            window.complianceRadarInstance.destroy();
        }
        
        window.complianceRadarInstance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: Object.keys(categoryScores),
                datasets: [{
                    label: '合规得分',
                    data: Object.values(categoryScores),
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: '#ddd' },
                        grid: { color: '#eee' },
                        suggestedMin: 0,
                        suggestedMax: 100,
                        ticks: { stepSize: 20 }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'R155 各类别合规得分',
                        font: { size: 16 }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('渲染雷达图失败:', error);
    }
}

/**
 * 渲染改进建议列表
 * @param {Array} recommendations - 建议列表
 */
function renderRecommendations(recommendations) {
    const container = document.getElementById('recommendationsList');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = `
            <div class="list-group-item success">
                <h4>✅ 保持良好实践</h4>
                <p>目前没有发现需要立即改进的问题，继续保持当前的安全开发生命周期（SDL）。</p>
            </div>
        `;
        return;
    }
    
    recommendations.forEach((rec, index) => {
        const item = document.createElement('div');
        item.className = 'list-group-item info';
        item.innerHTML = `
            <div class="list-item-header">
                <span class="badge">${index + 1}</span>
                <span class="rec-text">${rec}</span>
            </div>
        `;
        container.appendChild(item);
    });
}

/**
 * 显示推荐建议（用于扫描结果页面）
 * @param {Array} recommendations
 */
function showRecommendations(recommendations) {
    // 如果已经有了推荐的容器，就更新它
    const existingContainer = document.querySelector('.recommendations-summary');
    if (existingContainer) {
        existingContainer.remove();
    }
    
    if (!recommendations || recommendations.length === 0) return;
    
    const container = document.createElement('div');
    container.className = 'recommendations-summary';
    container.style.cssText = 'margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;';
    
    let html = '<h4>💡 改进建议</h4><ul style="margin: 0; padding-left: 20px;">';
    recommendations.forEach(rec => {
        html += `<li style="margin: 10px 0;">${rec}</li>`;
    });
    html += '</ul>';
    
    container.innerHTML = html;
    
    // 插入到合适位置（例如在漏洞表格之后）
    const vulnTable = document.querySelector('#vulnTable').closest('section');
    if (vulnTable) {
        vulnTable.after(container);
    }
}

// ============================================================
// 初始化与工具函数
// ============================================================

/**
 * 从 API 加载并显示合规报告
 * @param {string} taskId - 任务 ID
 */
async function loadComplianceReport(taskId) {
    try {
        const response = await fetch(`/api/compliance/${taskId}`);
        const data = await response.json();
        
        if (data.error) {
            console.warn('无法获取合规报告:', data.error);
            return;
        }
        
        currentComplianceData = data;
        
        // 更新 UI
        updateComplianceStats(data);
        
        // 如果有违规，默认显示第一个选项卡
        if (data.violations && data.violations.length > 0) {
            renderViolationsTable(data.violations);
        }
        
        // 渲染类别得分
        if (data.category_scores) {
            renderCategoryChart(data.category_scores);
        }
        
        // 渲染建议
        if (data.recommendations) {
            renderRecommendations(data.recommendations);
        }
        
    } catch (error) {
        console.error('加载合规报告失败:', error);
    }
}

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔒 R155 合规报告模块已加载');
});
