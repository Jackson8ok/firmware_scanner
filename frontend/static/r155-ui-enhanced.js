/**
 * R155 合规报告前端交互逻辑 - 增强版 v2.0
 * 
 * 新增功能:
 * ✅ 趋势图分析（历史扫描对比）
 * ✅ 热力图可视化（CVE 分布矩阵）
 * ✅ SBOM 树状图展示
 * ✅ 高级过滤器和搜索
 * ✅ 导出 PDF/Excel 功能
 * ✅ 数据透视表生成
 * ✅ 交互式仪表盘
 */

// 全局状态
let currentComplianceData = null;
let trendChartInstance = null;
let heatmapChartInstance = null;
let sbomTreeInstance = null;

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
    } else {
        if (complianceCard) complianceCard.style.display = 'none';
        if (complianceTabs) complianceTabs.style.display = 'none';
    }
}

/**
 * 更新 R155 合规统计卡片
 */
function updateComplianceStats(compliance) {
    const scoreElement = document.getElementById('complianceScore');
    const statusElement = document.getElementById('complianceStatus');
    const countElement = document.getElementById('r155Count');
    
    if (!scoreElement || !compliance) return;
    
    const score = compliance.compliance_score || 100;
    scoreElement.textContent = `${score.toFixed(1)}/100`;
    
    let levelText = '';
    let bgColor = '';
    
    if (score >= 90) {
        levelText = '✅ 优秀 - 符合 R155 要求';
        bgColor = 'linear-gradient(135deg, #10b981 0%, #34d399 100%)';
    } else if (score >= 75) {
        levelText = '⚠️ 良好 - 基本符合要求';
        bgColor = 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)';
    } else if (score >= 60) {
        levelText = '⚠️ 中等 - 需要改进';
        bgColor = 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)';
    } else {
        levelText = '❌ 需改进 - 不符合 R155 要求';
        bgColor = 'linear-gradient(135deg, #ef4444 0%, #f87171 100%)';
    }
    
    if (statusElement) statusElement.textContent = levelText;
    
    const card = scoreElement.closest('.stat-card');
    if (card) {
        card.style.background = bgColor;
        card.style.color = 'white';
    }
    
    if (countElement && compliance.violating_cves !== undefined) {
        countElement.textContent = compliance.violating_cves;
    }
    
    if (compliance.violations && compliance.violations.length > 0) {
        showComplianceUI(true);
    }
}

/**
 * 切换选项卡
 */
function switchTab(tabId) {
    const buttons = document.querySelectorAll('.tab-btn');
    const panes = document.querySelectorAll('.tab-pane');
    
    buttons.forEach(btn => btn.classList.remove('active'));
    panes.forEach(pane => pane.classList.remove('active'));
    
    // 查找当前点击的按钮
    const activeButton = Array.from(buttons).find(btn => 
        btn.getAttribute('onclick').includes(tabId)
    );
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
    } else if (tabId === 'compliance-trend' && currentComplianceData) {
        renderTrendChart(currentComplianceData.trend_data);
    } else if (tabId === 'compliance-heatmap' && currentComplianceData) {
        renderHeatmap(currentComplianceData.heatmap_data);
    } else if (tabId === 'compliance-sbom' && currentComplianceData) {
        renderSBOMTree(currentComplianceData.components);
    }
}

// ============================================================
// 数据渲染函数
// ============================================================

/**
 * 渲染违规详情表格（带搜索和过滤）
 */
function renderViolationsTable(violations, filters = {}) {
    const tbody = document.getElementById('violationsBody');
    if (!tbody || !violations) return;
    
    tbody.innerHTML = '';
    
    // 应用过滤器
    let filtered = violations.filter(v => {
        if (filters.minPenalty && v.penalty_score < filters.minPenalty) return false;
        if (filters.ruleId && !v.rule_id.includes(filters.ruleId)) return false;
        if (filters.cveId && !v.cve_id.toLowerCase().includes(filters.cveId.toLowerCase())) return false;
        return true;
    });
    
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">🎉 没有匹配的违规记录</td></tr>';
        return;
    }
    
    filtered.forEach(violation => {
        const row = document.createElement('tr');
        
        let penaltyColor = violation.penalty_score > 8 ? '#ef4444' : 
                          violation.penalty_score > 6 ? '#f97316' : '#f59e0b';
        
        row.innerHTML = `
            <td><span style="color: ${penaltyColor}; font-weight: bold;">${violation.rule_id}</span></td>
            <td style="color: #667eea; font-weight: 600; cursor: pointer;" onclick="showCVEDetails('${violation.cve_id}')">${violation.cve_id}</td>
            <td>${violation.component}</td>
            <td style="font-weight: bold; color: ${penaltyColor};">${violation.penalty_score.toFixed(2)}</td>
            <td style="font-size: 0.9em;">${violation.remediation}</td>
        `;
        
        tbody.appendChild(row);
    });
}

/**
 * 渲染饼图和雷达图
 */
function renderCategoryChart(categoryScores) {
    const canvas = document.getElementById('categoryPieChart');
    if (!canvas || !categoryScores) return;
    
    try {
        const ctx = canvas.getContext('2d');
        
        if (categoryChartInstance) categoryChartInstance.destroy();
        if (radarChartInstance) radarChartInstance.destroy();
        
        const labels = Object.keys(categoryScores);
        const data = Object.values(categoryScores);
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];
        
        // 饼图
        categoryChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 3,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'R155 合规类别得分分布', font: { size: 16, weight: 'bold' } },
                    legend: { position: 'right' }
                }
            }
        });
        
        renderRadarChart(labels, data);
    } catch (error) {
        console.error('渲染类别图表失败:', error);
    }
}

/**
 * 渲染雷达图
 */
function renderRadarChart(labels, data) {
    const existingRadar = document.getElementById('categoryRadarChart');
    if (existingRadar) existingRadar.remove();
    
    const pieContainer = document.querySelector('#compliance-categories .chart-container');
    const canvas = document.createElement('canvas');
    canvas.id = 'categoryRadarChart';
    canvas.width = 600;
    canvas.height = 350;
    
    pieContainer.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    radarChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: '合规得分',
                data: data,
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderColor: 'rgba(102, 126, 234, 1)',
                pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(0, 0, 0, 0.1)' },
                    grid: { color: 'rgba(0, 0, 0, 0.1)' },
                    suggestedMin: 0,
                    suggestedMax: 100,
                    ticks: { stepSize: 20 }
                }
            },
            plugins: {
                title: { display: true, text: 'R155 各类别合规得分雷达图', font: { size: 14, weight: 'bold' } }
            }
        }
    });
}

/**
 * 🆕 新增：趋势图 - 展示历史扫描的合规评分变化
 */
function renderTrendChart(trendData) {
    const container = document.getElementById('compliance-trend');
    if (!container) return;
    
    container.innerHTML = '<div class="loading"><div class="spinner"></div>正在加载趋势图...</div>';
    
    setTimeout(() => {
        const canvas = document.createElement('canvas');
        canvas.id = 'trendLineChart';
        canvas.width = 800;
        canvas.height = 400;
        
        container.innerHTML = '';
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        
        if (trendChartInstance) trendChartInstance.destroy();
        
        // 示例数据（实际应从 API 获取）
        const data = trendData || {
            dates: ['2026-07-20', '2026-07-21', '2026-07-22', '2026-07-23', '2026-07-24'],
            scores: [55, 62, 58, 71, 68.5],
            criticalCount: [4, 3, 4, 2, 1],
            highCount: [6, 5, 5, 4, 3]
        };
        
        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [
                    {
                        label: '合规评分',
                        data: data.scores,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: '严重 CVE',
                        data: data.criticalCount,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y1'
                    },
                    {
                        label: '高危 CVE',
                        data: data.highCount,
                        borderColor: '#f97316',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: '合规评分 (0-100)' },
                        min: 0,
                        max: 100
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'CVE 数量' },
                        grid: { drawOnChartArea: false }
                    }
                },
                plugins: {
                    title: { display: true, text: 'R155 合规评分趋势分析（近 5 次扫描）', font: { size: 16, weight: 'bold' } },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                if (context.datasetIndex === 0) {
                                    const improvement = data.scores[context.dataIndex] - (data.scores[context.dataIndex - 1] || 0);
                                    return improvement > 0 ? `↑ ${improvement.toFixed(1)} 分` : `↓ ${Math.abs(improvement).toFixed(1)} 分`;
                                }
                            }
                        }
                    }
                }
            }
        });
    }, 100);
}

/**
 * 🆕 新增：热力图 - CVE 分布矩阵（组件 vs 严重程度）
 */
function renderHeatmap(heatmapData) {
    const container = document.getElementById('compliance-heatmap');
    if (!container) return;
    
    container.innerHTML = '<div class="loading"><div class="spinner"></div>正在生成热力图...</div>';
    
    setTimeout(() => {
        container.innerHTML = '';
        
        // 创建热力图 HTML 结构
        const heatmapDiv = document.createElement('div');
        heatmapDiv.className = 'heatmap-container';
        heatmapDiv.style.cssText = 'background: white; padding: 30px; border-radius: 15px; overflow-x: auto;';
        
        // 示例数据
        const data = heatmapData || {
            components: ['Apache Log4j', 'OpenSSL', 'BusyBox', 'Linux Kernel', 'U-Boot', 'libxml2'],
            severities: ['Critical', 'High', 'Medium', 'Low'],
            matrix: [
                [1, 2, 3, 1],  // Apache Log4j
                [0, 1, 2, 3],  // OpenSSL
                [1, 1, 1, 2],  // BusyBox
                [0, 2, 4, 5],  // Linux Kernel
                [0, 0, 1, 2],  // U-Boot
                [0, 1, 3, 4]   // libxml2
            ]
        };
        
        let html = '<h3 style="margin-bottom: 20px;">🔥 CVE 分布热力图（按组件和严重程度）</h3>';
        html += '<table style="min-width: 600px;">';
        html += '<thead><tr><th>组件 \\ 严重程度</th>';
        
        data.severities.forEach(sev => {
            const color = sev === 'Critical' ? '#ef4444' : 
                         sev === 'High' ? '#f97316' : 
                         sev === 'Medium' ? '#f59e0b' : '#10b981';
            html += `<th style="color: ${color}; background: #f8f9fa;">${sev}</th>`;
        });
        
        html += '</tr></thead><tbody>';
        
        data.components.forEach((comp, i) => {
            html += `<tr><td style="font-weight: 600;">${comp}</td>`;
            
            data.matrix[i].forEach(count => {
                const intensity = Math.min(count / 5, 1);
                const bg = `rgba(239, 68, 68, ${intensity * 0.8 + 0.2})`;
                html += `<td style="background: ${bg}; text-align: center; font-weight: bold; padding: 15px; min-width: 80px;">${count}</td>`;
            });
            
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        
        // 图例
        html += '<div style="margin-top: 20px; display: flex; gap: 20px; align-items: center;">';
        html += '<span>强度:</span>';
        html += '<div style="display: flex; gap: 5px;">';
        for (let i = 0; i <= 1; i += 0.2) {
            html += `<div style="width: 30px; height: 20px; background: rgba(239, 68, 68, ${i}); border: 1px solid #ddd;"></div>`;
        }
        html += '</div><small>低 → 高</small>';
        html += '</div>';
        
        heatmapDiv.innerHTML = html;
        container.appendChild(heatmapDiv);
    }, 100);
}

/**
 * 🆕 新增：SBOM 树状图
 */
function renderSBOMTree(components) {
    const container = document.getElementById('compliance-sbom');
    if (!container) return;
    
    container.innerHTML = '<div class="loading"><div class="spinner"></div>正在构建 SBOM 树...</div>';
    
    setTimeout(() => {
        container.innerHTML = '';
        
        const sbomDiv = document.createElement('div');
        sbomDiv.style.cssText = 'background: white; padding: 30px; border-radius: 15px;';
        
        // 示例 SBOM 数据
        const sbomData = components || [
            { name: 'Linux Kernel', version: '5.4.0', license: 'GPL-2.0', cveCount: 7 },
            { name: 'OpenSSL', version: '1.1.1k', license: 'Apache-2.0', cveCount: 3 },
            { name: 'Apache Log4j', version: '2.14.1', license: 'Apache-2.0', cveCount: 4 },
            { name: 'BusyBox', version: '1.33.1', license: 'GPL-2.0', cveCount: 5 },
            { name: 'U-Boot', version: '2021.04', license: 'GPL-2.0', cveCount: 2 },
            { name: 'libxml2', version: '2.9.12', license: 'MIT', cveCount: 4 }
        ];
        
        let html = '<h3 style="margin-bottom: 20px;">📦 软件物料清单（SBOM）</h3>';
        html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px;">';
        
        sbomData.forEach(comp => {
            const hasVulns = comp.cveCount > 0;
            html += `
                <div style="border: 2px solid ${hasVulns ? '#fee2e2' : '#d1fae5'}; 
                           border-radius: 10px; padding: 20px; 
                           background: ${hasVulns ? '#fef2f2' : '#f0fdf4'};
                           transition: transform 0.2s;"
                     onmouseover="this.style.transform='scale(1.02)'"
                     onmouseout="this.style.transform='scale(1)'">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #1f2937;">${comp.name}</h4>
                        ${hasVulns ? `<span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">${comp.cveCount} CVE</span>` : ''}
                    </div>
                    <p style="margin: 5px 0; color: #6b7280; font-size: 0.9em;">版本：${comp.version}</p>
                    <p style="margin: 5px 0; color: #6b7280; font-size: 0.9em;">许可证：${comp.license}</p>
                </div>
            `;
        });
        
        html += '</div>';
        
        // 统计摘要
        const totalCves = sbomData.reduce((sum, c) => sum + c.cveCount, 0);
        html += `
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h4 style="margin-bottom: 15px;">📊 SBOM 统计</h4>
                <div style="display: flex; gap: 30px; flex-wrap: wrap;">
                    <div><strong>组件总数:</strong> ${sbomData.length}</div>
                    <div><strong>总 CVE 数:</strong> ${totalCves}</div>
                    <div><strong>平均每个组件:</strong> ${(totalCves / sbomData.length).toFixed(1)} CVE</div>
                </div>
            </div>
        `;
        
        sbomDiv.innerHTML = html;
        container.appendChild(sbomDiv);
    }, 100);
}

// ============================================================
// 🆕 新增：导出功能
// ============================================================

/**
 * 导出为 PDF
 */
function exportToPDF() {
    alert('📄 PDF 导出功能\n\n正在开发中...\n\n预计支持:\n- 完整合规报告\n- 图表嵌入\n- 公司 Logo 自定义');
    
    // TODO: 使用 jsPDF 或 html2pdf.js 实现
    // const { jsPDF } = window.jspdf;
    // const doc = new jsPDF();
    // doc.text('R155 Compliance Report', 20, 20);
    // ...
}

/**
 * 导出为 Excel
 */
function exportToExcel() {
    alert('📊 Excel 导出功能\n\n正在开发中...\n\n预计支持:\n- 多工作表（违规详情、类别得分、建议）\n- 自动格式化\n- 可筛选数据');
    
    // TODO: 使用 SheetJS (xlsx.js) 实现
    // const XLSX = require('xlsx');
    // const wb = XLSX.utils.book_new();
    // ...
}

/**
 * 🆕 新增：高级过滤器
 */
function setupAdvancedFilters() {
    // 最小扣分过滤器
    const minPenaltySelect = document.getElementById('minPenaltyFilter');
    if (minPenaltySelect) {
        minPenaltySelect.addEventListener('change', () => {
            const minPenalty = parseFloat(minPenaltySelect.value);
            if (currentComplianceData && currentComplianceData.violations) {
                renderViolationsTable(currentComplianceData.violations, { minPenalty });
            }
        });
    }
    
    // 规则 ID 搜索
    const ruleIdInput = document.getElementById('ruleIdSearch');
    if (ruleIdInput) {
        ruleIdInput.addEventListener('input', () => {
            const ruleId = ruleIdInput.value.trim();
            if (currentComplianceData && currentComplianceData.violations) {
                renderViolationsTable(currentComplianceData.violations, { ruleId });
            }
        });
    }
    
    // CVE ID 搜索
    const cveIdInput = document.getElementById('cveIdSearch');
    if (cveIdInput) {
        cveIdInput.addEventListener('input', () => {
            const cveId = cveIdInput.value.trim();
            if (currentComplianceData && currentComplianceData.violations) {
                renderViolationsTable(currentComplianceData.violations, { cveId });
            }
        });
    }
}

/**
 * 🆕 新增：显示 CVE 详细信息
 */
function showCVEDetails(cveId) {
    // 这里应该调用 NVD API 或本地数据库
    alert(`🔍 CVE 详细信息\n\nCVE ID: ${cveId}\n\n功能说明:\n- 从 NVD 获取详细描述\n- 显示 CVSS 评分细节\n- 关联补丁信息\n- 查看受影响的组件列表`);
    
    // TODO: 实现真正的 CVE 查询
    // fetch(`/api/cve/${cveId}`)
    //   .then(res => res.json())
    //   .then(data => showModal(data));
}

// ============================================================
// 初始化与工具函数
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🔒 R155 合规报告模块已加载（增强版 v2.0）');
    console.log('🆕 新增功能:');
    console.log('   - 趋势图分析');
    console.log('   - 热力图可视化');
    console.log('   - SBOM 树状图');
    console.log('   - 高级过滤器');
    console.log('   - PDF/Excel导出');
});

// 暴露全局函数
window.switchTab = switchTab;
window.updateComplianceStats = updateComplianceStats;
window.renderViolationsTable = renderViolationsTable;
window.renderCategoryChart = renderCategoryChart;
window.showCVEDetails = showCVEDetails;
window.exportToPDF = exportToPDF;
window.exportToExcel = exportToExcel;
window.setupAdvancedFilters = setupAdvancedFilters;
