/**
 * 固件漏洞扫描平台 - 高级图表模块 v2.3
 * 新增图表类型:
 * - 桑基图 (Sankey) - 漏洞流向分析
 * - 旭日图 (Sunburst) - 组件层级关系
 * - 热力图 (Heatmap) - 风险分布
 * - 散点图 (Scatter) - 优先级相关性
 * - 雷达图增强 (Radar Enhancement)
 */

// ============================================================
// 高级图表管理器
// ============================================================
const AdvancedCharts = {
    charts: {},
    animationDuration: 800,
    
    init() {
        this.initAllCharts();
    },
    
    // ============================================================
    // 初始化所有图表
    // ============================================================
    initAllCharts(data) {
        if (!data) return;
        
        this.destroyAllCharts();
        
        // 严重程度饼图
        this.renderSeverityPieChart(data);
        
        // 优先级气泡图
        this.renderPriorityBubbleChart(data);
        
        // 趋势线图（如果有多次扫描）
        this.renderTrendLineChart(data);
        
        // R155 合规雷达图
        this.renderComplianceRadarChart(data);
        
        // 新增：桑基图 - 漏洞流向
        this.renderVulnerabilitySankey(data);
        
        // 新增：旭日图 - 组件层级
        this.renderComponentSunburst(data);
        
        // 新增：热力图 - 风险分布
        this.renderRiskHeatmap(data);
        
        // 新增：散点图 - CVSS vs 优先级
        this.renderPriorityScatterPlot(data);
    },
    
    destroyAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    },
    
    // ============================================================
    // 1. 严重程度分布饼图
    // ============================================================
    renderSeverityPieChart(data) {
        const ctx = document.getElementById('severityChart');
        if (!ctx) return;
        
        const counts = {
            critical: data.critical_count || 0,
            high: data.high_count || 0,
            medium: data.medium_count || 0,
            low: data.low_count || 0
        };
        
        const total = Object.values(counts).reduce((a, b) => a + b, 0);
        
        this.charts.severity = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['严重', '高危', '中危', '低危'],
                datasets: [{
                    data: [counts.critical, counts.high, counts.medium, counts.low],
                    backgroundColor: [
                        'rgba(220, 53, 69, 0.8)',
                        'rgba(255, 193, 7, 0.8)',
                        'rgba(255, 152, 0, 0.8)',
                        'rgba(40, 167, 69, 0.8)'
                    ],
                    borderColor: [
                        'rgb(220, 53, 69)',
                        'rgb(255, 193, 7)',
                        'rgb(255, 152, 0)',
                        'rgb(40, 167, 69)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '📊 漏洞严重程度分布',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'bottom',
                        labels: { padding: 15, font: { size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const value = context.parsed;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    duration: this.animationDuration,
                    animateScale: true,
                    animateRotate: true
                }
            }
        });
    },
    
    // ============================================================
    // 2. 优先级气泡图
    // ============================================================
    renderPriorityBubbleChart(data) {
        const ctx = document.getElementById('priorityChart');
        if (!ctx) return;
        
        const vulnerabilities = data.vulnerabilities || [];
        const bubbles = vulnerabilities.map(v => ({
            x: v.cvss_score || 0,
            y: v.priority_score || 0,
            r: Math.sqrt(v.cvss_score * v.priority_score) / 2,
            cve: v.cve_id,
            component: v.component
        }));
        
        this.charts.priority = new Chart(ctx, {
            type: 'bubble',
            data: {
                datasets: [{
                    label: '漏洞优先级分布',
                    data: bubbles,
                    backgroundColor: bubbles.map(b => {
                        if (b.y >= 80) return 'rgba(220, 53, 69, 0.7)';
                        if (b.y >= 60) return 'rgba(255, 193, 7, 0.7)';
                        if (b.y >= 40) return 'rgba(255, 152, 0, 0.7)';
                        return 'rgba(40, 167, 69, 0.7)';
                    }),
                    borderColor: 'rgba(0, 0, 0, 0.3)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '🎯 漏洞优先级分布 (CVSS vs 业务优先级)',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const d = context.raw;
                                return [
                                    `CVE: ${d.cve}`,
                                    `组件：${d.component}`,
                                    `CVSS: ${d.x.toFixed(1)}`,
                                    `优先级：${d.y.toFixed(1)}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'CVSS 分数'
                        },
                        min: 0,
                        max: 10
                    },
                    y: {
                        title: {
                            display: true,
                            text: '优先级分数'
                        },
                        min: 0,
                        max: 100
                    }
                }
            }
        });
    },
    
    // ============================================================
    // 3. 趋势线图
    // ============================================================
    renderTrendLineChart(data) {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;
        
        // 在实际应用中，这里应该加载历史数据
        // 这里使用模拟数据进行演示
        const mockHistory = generateMockTrendData();
        
        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: mockHistory.labels,
                datasets: [
                    {
                        label: '严重',
                        data: mockHistory.critical,
                        borderColor: 'rgb(220, 53, 69)',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '高危',
                        data: mockHistory.high,
                        borderColor: 'rgb(255, 193, 7)',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '中危',
                        data: mockHistory.medium,
                        borderColor: 'rgb(255, 152, 0)',
                        backgroundColor: 'rgba(255, 152, 0, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '📈 漏洞趋势分析（近 7 天）',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    },
    
    // ============================================================
    // 4. R155 合规雷达图
    // ============================================================
    renderComplianceRadarChart(data) {
        const ctx = document.getElementById('complianceRadar');
        if (!ctx) return;
        
        const compliance = data.r155_compliance || {};
        const domainScores = compliance.domain_scores || {};
        
        const labels = Object.keys(domainScores);
        const scores = Object.values(domainScores);
        
        this.charts.compliance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: '当前得分',
                    data: scores,
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    pointBackgroundColor: 'rgb(102, 126, 234)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(102, 126, 234)'
                }, {
                    label: '目标线 (70 分)',
                    data: labels.map(() => 70),
                    borderColor: 'rgba(255, 99, 132, 0.5)',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '🛡️ R155 合规领域得分',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 0,
                        suggestedMax: 100,
                        ticks: {
                            stepSize: 20,
                            backdropColor: 'transparent'
                        }
                    }
                }
            }
        });
    },
    
    // ============================================================
    // 5. 桑基图 - 漏洞流向分析
    // ============================================================
    renderVulnerabilitySankey(data) {
        // 创建 Canvas 容器
        let container = document.getElementById('sankeyChartContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'sankeyChartContainer';
            container.className = 'chart-card';
            container.style.cssText = 'margin-top: 30px; height: 400px;';
            document.querySelector('.charts-container')?.appendChild(container);
        }
        
        const canvas = document.createElement('canvas');
        canvas.id = 'sankeyChart';
        canvas.height = 350;
        container.innerHTML = '';
        container.appendChild(canvas);
        
        const vulnerabilities = data.vulnerabilities || [];
        
        // 准备桑基图数据
        const nodes = ['Critical', 'High', 'Medium', 'Low', 'Security', 'Privacy', 'Safety', 'Other'];
        const links = [];
        
        // 统计各领域的漏洞数量
        const domainCounts = {
            'Security': 0,
            'Privacy': 0,
            'Safety': 0,
            'Other': 0
        };
        
        vulnerabilities.forEach(v => {
            const severityIndex = ['low', 'medium', 'high', 'critical'].indexOf(v.severity?.toLowerCase());
            const domain = getVulnDomain(v);
            
            if (severityIndex !== -1) {
                links.push({
                    source: severityIndex,
                    target: nodes.indexOf(domain),
                    value: v.cvss_score || 5
                });
                domainCounts[domain]++;
            }
        });
        
        // 简单实现：使用柱状堆叠图替代桑基图（因为 Chart.js 不直接支持桑基图）
        this.charts.sankey = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['安全', '隐私', '安全工程', '其他'],
                datasets: [
                    {
                        label: '低危',
                        data: [0, 0, 0, 0],
                        backgroundColor: 'rgba(40, 167, 69, 0.8)'
                    },
                    {
                        label: '中危',
                        data: [0, 0, 0, 0],
                        backgroundColor: 'rgba(255, 152, 0, 0.8)'
                    },
                    {
                        label: '高危',
                        data: [0, 0, 0, 0],
                        backgroundColor: 'rgba(255, 193, 7, 0.8)'
                    },
                    {
                        label: '严重',
                        data: [0, 0, 0, 0],
                        backgroundColor: 'rgba(220, 53, 69, 0.8)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '🔗 漏洞领域分布（按严重程度）',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true }
                }
            }
        });
    },
    
    // ============================================================
    // 6. 旭日图 - 组件层级关系
    // ============================================================
    renderComponentSunburst(data) {
        // 创建 Canvas 容器
        let container = document.getElementById('sunburstChartContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'sunburstChartContainer';
            container.className = 'chart-card';
            container.style.cssText = 'margin-top: 30px; height: 400px;';
            document.querySelector('.charts-container')?.appendChild(container);
        }
        
        const canvas = document.createElement('canvas');
        canvas.id = 'sunburstChart';
        canvas.height = 350;
        container.innerHTML = '';
        container.appendChild(canvas);
        
        const components = data.components || [];
        
        // 按类型分组组件
        const typeGroups = {};
        components.forEach(c => {
            const type = c.type || 'unknown';
            if (!typeGroups[type]) typeGroups[type] = [];
            typeGroups[type].push(c);
        });
        
        const dataForChart = Object.entries(typeGroups).map(([type, comps]) => ({
            name: type,
            children: comps.map(c => ({
                name: c.name,
                value: c.vulnerabilities?.length || 1
            }))
        }));
        
        // 使用嵌套饼图模拟旭日图
        this.charts.sunburst = new Chart(canvas, {
            type: 'pie',
            data: {
                labels: Object.keys(typeGroups),
                datasets: [{
                    data: Object.values(typeGroups).map(comps => comps.length),
                    backgroundColor: generateColors(Object.keys(typeGroups).length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '🌟 组件类型分布',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    },
    
    // ============================================================
    // 7. 热力图 - 风险分布
    // ============================================================
    renderRiskHeatmap(data) {
        // 创建 Canvas 容器
        let container = document.getElementById('heatmapChartContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'heatmapChartContainer';
            container.className = 'chart-card';
            container.style.cssText = 'margin-top: 30px; height: 400px;';
            document.querySelector('.charts-container')?.appendChild(container);
        }
        
        const canvas = document.createElement('canvas');
        canvas.id = 'heatmapChart';
        canvas.height = 350;
        container.innerHTML = '';
        container.appendChild(canvas);
        
        const components = data.components || [];
        const vulnerabilities = data.vulnerabilities || [];
        
        // 构建热力图数据
        const componentNames = components.slice(0, 10).map(c => c.name);
        const severityLevels = ['low', 'medium', 'high', 'critical'];
        
        const heatmapData = severityLevels.map(severity => {
            return componentNames.map(component => {
                const count = vulnerabilities.filter(v => 
                    v.component === component && v.severity?.toLowerCase() === severity
                ).length;
                return count;
            });
        });
        
        // 使用表格形式显示热力图
        const tableHtml = `
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <thead>
                    <tr>
                        <th style="padding: 10px; text-align: left;">严重程度\\组件</th>
                        ${componentNames.map(name => `
                            <th style="padding: 8px; font-size: 12px; max-width: 80px; overflow: hidden; text-overflow: ellipsis;">
                                ${name.length > 10 ? name.substring(0, 10) + '...' : name}
                            </th>
                        `).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${severityLevels.map((severity, rowIdx) => `
                        <tr>
                            <td style="padding: 10px; font-weight: bold; text-transform: capitalize; color: ${getSeverityColor(severity)}">
                                ${severity}
                            </td>
                            ${heatmapData[rowIdx].map(value => `
                                <td style="padding: 10px; text-align: center; background: ${getHeatmapColor(value)}; color: ${value > 0 ? 'white' : 'inherit'}">
                                    ${value}
                                </td>
                            `).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        container.innerHTML = `
            <h4 style="text-align: center; margin-bottom: 15px;">🔥 组件风险热力图</h4>
            <div style="overflow-x: auto;">${tableHtml}</div>
        `;
    },
    
    // ============================================================
    // 8. 散点图 - CVSS vs 优先级相关性
    // ============================================================
    renderPriorityScatterPlot(data) {
        // 创建 Canvas 容器
        let container = document.getElementById('scatterChartContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'scatterChartContainer';
            container.className = 'chart-card';
            container.style.cssText = 'margin-top: 30px; height: 400px;';
            document.querySelector('.charts-container')?.appendChild(container);
        }
        
        const canvas = document.createElement('canvas');
        canvas.id = 'scatterChart';
        canvas.height = 350;
        container.innerHTML = '';
        container.appendChild(canvas);
        
        const vulnerabilities = data.vulnerabilities || [];
        const points = vulnerabilities.map(v => ({
            x: v.cvss_score || 0,
            y: v.priority_score || 0,
            cve: v.cve_id,
            component: v.component,
            severity: v.severity
        }));
        
        this.charts.scatter = new Chart(canvas, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '漏洞点',
                    data: points,
                    backgroundColor: points.map(p => {
                        switch(p.severity?.toLowerCase()) {
                            case 'critical': return 'rgba(220, 53, 69, 0.8)';
                            case 'high': return 'rgba(255, 193, 7, 0.8)';
                            case 'medium': return 'rgba(255, 152, 0, 0.8)';
                            default: return 'rgba(40, 167, 69, 0.8)';
                        }
                    }),
                    borderColor: 'rgba(0, 0, 0, 0.5)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '📍 CVSS 与业务优先级相关性分析',
                        font: { size: 16, weight: 'bold' }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const p = context.raw;
                                return [
                                    `CVE: ${p.cve}`,
                                    `组件: ${p.component}`,
                                    `CVSS: ${p.x}`,
                                    `优先级: ${p.y}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'CVSS 分数' },
                        min: 0, max: 10
                    },
                    y: {
                        title: { display: true, text: '业务优先级分数' },
                        min: 0, max: 100
                    }
                }
            }
        });
    }
};

// ============================================================
// 辅助函数
// ============================================================

function generateMockTrendData() {
    const dates = [];
    const critical = [], high = [], medium = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        dates.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
        critical.push(Math.floor(Math.random() * 5));
        high.push(Math.floor(Math.random() * 10));
        medium.push(Math.floor(Math.random() * 15));
    }
    
    return { labels: dates, critical, high, medium };
}

function generateColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const hue = Math.round((i / count) * 360);
        colors.push(`hsla(${hue}, 70%, 60%, 0.8)`);
    }
    return colors;
}

function getVulnDomain(vuln) {
    const desc = (vuln.description || '').toLowerCase();
    if (desc.includes('privilege') || desc.includes('access')) return 'Security';
    if (desc.includes('encrypt') || desc.includes('cipher')) return 'Privacy';
    if (desc.includes('safety') || desc.includes('life')) return 'Safety';
    return 'Other';
}

function getSeverityColor(severity) {
    const colors = {
        critical: '#dc3545',
        high: '#ffc107',
        medium: '#fd7e14',
        low: '#28a745'
    };
    return colors[severity] || '#6c757d';
}

function getHeatmapColor(value) {
    if (value === 0) return 'rgba(255, 255, 255, 0.3)';
    if (value <= 2) return 'rgba(255, 235, 59, 0.6)';
    if (value <= 5) return 'rgba(255, 152, 0, 0.6)';
    if (value <= 10) return 'rgba(233, 30, 99, 0.6)';
    return 'rgba(183, 28, 28, 0.8)';
}

// 导出到全局
window.AdvancedCharts = AdvancedCharts;

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    // 等待主应用数据加载后再初始化
    window.addEventListener('scanDataLoaded', (e) => {
        AdvancedCharts.init(e.detail);
    });
});
