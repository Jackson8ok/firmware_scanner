/**
 * 固件扫描平台 - 图表组件库
 * 纯原生 Canvas 2D，无外部依赖
 */

// ============================================================
// 通用图表配置
// ============================================================
const CHART_COLORS = {
    primary: '#667eea',
    secondary: '#764ba2',
    success: '#28a745',
    warning: '#ffc107',
    danger: '#dc3545',
    info: '#17a2b8'
};

const SEVERITY_COLORS = {
    critical: '#dc3545',
    high: '#fd7e14',
    medium: '#ffc107',
    low: '#28a745'
};

// ============================================================
// 1. 饼图 - 严重程度分布
// ============================================================
class SeverityPieChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.data = null;
    }

    render(data) {
        this.data = data;
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        // 清空画布
        this.ctx.clearRect(0, 0, width, height);
        
        const counts = {
            critical: data.critical_count || 0,
            high: data.high_count || 0,
            medium: data.medium_count || 0,
            low: data.low_count || 0
        };
        
        const total = Object.values(counts).reduce((a, b) => a + b, 0);
        
        if (total === 0) {
            this.drawNoDataText(width, height, '暂无漏洞数据');
            return;
        }
        
        // 绘制标题
        this.drawTitle('严重程度分布', width / 2, 25);
        
        // 饼图参数
        const centerX = width / 2;
        const centerY = height / 2 + 20;
        const radius = Math.min(width, height) / 2.5;
        
        const labels = ['严重', '高危', '中危', '低危'];
        const keys = ['critical', 'high', 'medium', 'low'];
        
        let startAngle = -Math.PI / 2;
        let endAngle = startAngle;
        
        // 绘制饼图和百分比标签
        keys.forEach((key, index) => {
            const sliceAngle = (counts[key] / total) * 2 * Math.PI;
            
            if (sliceAngle > 0) {
                this.ctx.beginPath();
                this.ctx.moveTo(centerX, centerY);
                this.ctx.arc(centerX, centerY, radius, endAngle, endAngle + sliceAngle);
                this.ctx.closePath();
                this.ctx.fillStyle = SEVERITY_COLORS[key];
                this.ctx.fill();
                this.ctx.strokeStyle = '#fff';
                this.ctx.lineWidth = 2;
                this.ctx.stroke();
                
                // 绘制百分比标签
                const labelAngle = endAngle + sliceAngle / 2;
                const labelRadius = radius * 0.7;
                const labelX = centerX + Math.cos(labelAngle) * labelRadius;
                const labelY = centerY + Math.sin(labelAngle) * labelRadius;
                
                const percentage = ((counts[key] / total) * 100).toFixed(1);
                
                if (percentage > 5) {
                    this.ctx.fillStyle = '#fff';
                    this.ctx.font = 'bold 12px Arial';
                    this.ctx.textAlign = 'center';
                    this.ctx.fillText(`${percentage}%`, labelX, labelY);
                }
                
                endAngle += sliceAngle;
            } else {
                endAngle += sliceAngle;
            }
        });
        
        // 绘制图例
        this.drawLegend(keys, labels, counts, radius + 30, width);
    }

    drawTitle(text, x, y) {
        this.ctx.fillStyle = '#333';
        this.ctx.font = 'bold 16px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, x, y);
    }

    drawLegend(keys, labels, counts, offsetX, canvasWidth) {
        const legendX = canvasWidth - 140;
        const legendY = 50;
        
        keys.forEach((key, index) => {
            const count = counts[key];
            
            this.ctx.fillStyle = SEVERITY_COLORS[key];
            this.ctx.fillRect(legendX, legendY + index * 30, 15, 15);
            
            this.ctx.fillStyle = '#333';
            this.ctx.font = '13px Arial';
            this.ctx.textAlign = 'left';
            this.ctx.fillText(`${labels[index]}: ${count}`, legendX + 20, legendY + index * 30 + 12);
        });
    }

    drawNoDataText(width, height, text) {
        this.ctx.fillStyle = '#999';
        this.ctx.font = '14px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, width / 2, height / 2);
    }
}

// ============================================================
// 2. 柱状图 - Top 10 高优先级漏洞
// ============================================================
class PriorityBarChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.data = null;
    }

    render(data) {
        this.data = data;
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.ctx.clearRect(0, 0, width, height);
        
        const vulns = data.vulnerabilities || [];
        
        if (vulns.length === 0) {
            this.drawNoDataText(width, height, '暂无漏洞数据');
            return;
        }
        
        // 绘制标题
        this.drawTitle('Top 10 高优先级漏洞', width / 2, 25);
        
        // 取前 10 个
        const topVulns = vulns.slice(0, 10);
        
        const padding = { top: 50, right: 40, bottom: 70, left: 70 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;
        
        const barWidth = chartWidth / topVulns.length - 15;
        const maxPriority = Math.max(...topVulns.map(v => v.priority_score || 0));
        
        // 绘制坐标轴
        this.drawAxes(padding, width, height);
        
        // 绘制条形图
        topVulns.forEach((vuln, index) => {
            const x = padding.left + 8 + index * (barWidth + 15);
            const barHeight = ((vuln.priority_score || 0) / maxPriority) * chartHeight;
            const y = height - padding.bottom - barHeight;
            
            // 渐变色
            const gradient = this.ctx.createLinearGradient(x, y, x, height - padding.bottom);
            gradient.addColorStop(0, '#667eea');
            gradient.addColorStop(1, '#764ba2');
            
            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(x, y, barWidth, barHeight);
            
            // CVE ID 标签
            this.ctx.fillStyle = '#333';
            this.ctx.font = 'bold 10px Arial';
            this.ctx.textAlign = 'center';
            
            const shortId = vuln.cve_id.length > 12 ? 
                vuln.cve_id.substring(0, 10) + '..' : 
                vuln.cve_id;
            this.ctx.fillText(shortId, x + barWidth / 2, height - padding.bottom + 15);
            
            // 数值标签
            this.ctx.fillStyle = '#666';
            this.ctx.font = '11px Arial';
            this.ctx.fillText(
                (vuln.priority_score || 0).toFixed(3),
                x + barWidth / 2,
                y - 5
            );
        });
        
        // Y 轴标题
        this.ctx.save();
        this.ctx.translate(20, height / 2);
        this.ctx.rotate(-Math.PI / 2);
        this.ctx.fillStyle = '#333';
        this.ctx.font = '13px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('优先级分数', 0, 0);
        this.ctx.restore();
        
        // X 轴标题
        this.ctx.fillStyle = '#333';
        this.ctx.font = '13px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('CVE ID', width / 2, height - 15);
    }

    drawAxes(padding, width, height) {
        this.ctx.strokeStyle = '#ccc';
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(padding.left, padding.top);
        this.ctx.lineTo(padding.left, height - padding.bottom);
        this.ctx.lineTo(width - padding.right, height - padding.bottom);
        this.ctx.stroke();
    }

    drawTitle(text, x, y) {
        this.ctx.fillStyle = '#333';
        this.ctx.font = 'bold 16px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, x, y);
    }

    drawNoDataText(width, height, text) {
        this.ctx.fillStyle = '#999';
        this.ctx.font = '14px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, width / 2, height / 2);
    }
}

// ============================================================
// 3. 折线图 - 扫描历史趋势
// ============================================================
class TrendLineChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.data = null;
    }

    render(scanHistory) {
        this.data = scanHistory;
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.ctx.clearRect(0, 0, width, height);
        
        if (!scanHistory || scanHistory.length === 0) {
            this.drawNoDataText(width, height, '暂无扫描历史');
            return;
        }
        
        // 绘制标题
        this.drawTitle('近 7 天扫描趋势', width / 2, 25);
        
        const padding = { top: 50, right: 40, bottom: 60, left: 70 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;
        
        // 准备数据
        const dates = scanHistory.map(d => d.date);
        const cveCounts = scanHistory.map(d => d.total_cves);
        const criticalCounts = scanHistory.map(d => d.critical_count);
        
        const maxCve = Math.max(...cveCounts, 1);
        
        // 绘制坐标轴
        this.drawAxes(padding, width, height);
        
        // 绘制网格线
        this.drawGridLines(padding, chartWidth, chartHeight, maxCve);
        
        // 绘制 CVE 总数折线
        this.drawTrendLine(
            padding, chartWidth, chartHeight,
            dates, cveCounts, maxCve,
            CHART_COLORS.primary, 'Total CVEs'
        );
        
        // 绘制严重漏洞折线
        this.drawTrendLine(
            padding, chartWidth, chartHeight,
            dates, criticalCounts, maxCve,
            CHART_COLORS.danger, 'Critical'
        );
        
        // X 轴日期标签
        this.ctx.fillStyle = '#666';
        this.ctx.font = '11px Arial';
        this.ctx.textAlign = 'center';
        
        dates.forEach((date, index) => {
            const x = padding.left + (index / (dates.length - 1)) * chartWidth;
            this.ctx.fillText(date, x, height - padding.bottom + 20);
        });
    }

    drawAxes(padding, width, height) {
        this.ctx.strokeStyle = '#ccc';
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(padding.left, padding.top);
        this.ctx.lineTo(padding.left, height - padding.bottom);
        this.ctx.lineTo(width - padding.right, height - padding.bottom);
        this.ctx.stroke();
    }

    drawGridLines(padding, chartWidth, chartHeight, maxVal) {
        this.ctx.strokeStyle = '#eee';
        this.ctx.lineWidth = 1;
        
        for (let i = 0; i <= 5; i++) {
            const y = padding.top + (i / 5) * chartHeight;
            this.ctx.beginPath();
            this.ctx.moveTo(padding.left, y);
            this.ctx.lineTo(width - padding.right, y);
            this.ctx.stroke();
            
            // Y 轴数值标签
            const value = Math.round(maxVal - (i / 5) * maxVal);
            this.ctx.fillStyle = '#666';
            this.ctx.font = '11px Arial';
            this.ctx.textAlign = 'right';
            this.ctx.fillText(value.toString(), padding.left - 10, y + 4);
        }
    }

    drawTrendLine(padding, chartWidth, chartHeight, dates, values, maxVal, color, label) {
        const points = dates.map((_, index) => ({
            x: padding.left + (index / (dates.length - 1)) * chartWidth,
            y: padding.top + chartHeight - (values[index] / maxVal) * chartHeight
        }));
        
        // 绘制线条
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        this.ctx.moveTo(points[0].x, points[0].y);
        
        for (let i = 1; i < points.length; i++) {
            this.ctx.lineTo(points[i].x, points[i].y);
        }
        
        this.ctx.stroke();
        
        // 绘制数据点
        points.forEach(point => {
            this.ctx.fillStyle = color;
            this.ctx.beginPath();
            this.ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
            this.ctx.fill();
            
            this.ctx.fillStyle = '#fff';
            this.ctx.beginPath();
            this.ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }

    drawTitle(text, x, y) {
        this.ctx.fillStyle = '#333';
        this.ctx.font = 'bold 16px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, x, y);
    }

    drawNoDataText(width, height, text) {
        this.ctx.fillStyle = '#999';
        this.ctx.font = '14px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, width / 2, height / 2);
    }
}

// ============================================================
// 4. 雷达图 - R155 合规评分
// ============================================================
class ComplianceRadarChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.data = null;
    }

    render(complianceData) {
        this.data = complianceData;
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.ctx.clearRect(0, 0, width, height);
        
        // 绘制标题
        this.drawTitle('R155 合规评分', width / 2, 25);
        
        const centerX = width / 2;
        const centerY = height / 2 + 20;
        const radius = Math.min(width, height) / 3;
        
        // 6 个维度
        const dimensions = [
            '软件供应链安全',
            '漏洞管理',
            '产品安全',
            '认证机制',
            '加密保护',
            '日志审计'
        ];
        
        // 得分（0-100）
        const scores = [
            complianceData.software_supply_chain || 75,
            complianceData.vulnerability_management || 60,
            complianceData.product_security || 80,
            complianceData.auth_mechanism || 70,
            complianceData.encryption || 65,
            complianceData.logging_audit || 85
        ];
        
        const angleStep = (Math.PI * 2) / dimensions.length;
        const startAngle = -Math.PI / 2;
        
        // 绘制背景五边形
        for (let i = 1; i <= 4; i++) {
            this.ctx.beginPath();
            
            for (let j = 0; j < dimensions.length; j++) {
                const angle = startAngle + j * angleStep;
                const r = (radius * i) / 4;
                const x = centerX + Math.cos(angle) * r;
                const y = centerY + Math.sin(angle) * r;
                
                if (j === 0) {
                    this.ctx.moveTo(x, y);
                } else {
                    this.ctx.lineTo(x, y);
                }
            }
            
            this.ctx.closePath();
            this.ctx.strokeStyle = '#ddd';
            this.ctx.lineWidth = 1;
            this.ctx.stroke();
        }
        
        // 绘制数据多边形
        this.ctx.beginPath();
        
        for (let i = 0; i < dimensions.length; i++) {
            const angle = startAngle + i * angleStep;
            const r = (scores[i] / 100) * radius;
            const x = centerX + Math.cos(angle) * r;
            const y = centerY + Math.sin(angle) * r;
            
            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }
        
        this.ctx.closePath();
        this.ctx.fillStyle = 'rgba(102, 126, 234, 0.3)';
        this.ctx.fill();
        this.ctx.strokeStyle = CHART_COLORS.primary;
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        // 绘制数据点和标签
        for (let i = 0; i < dimensions.length; i++) {
            const angle = startAngle + i * angleStep;
            const r = radius;
            const x = centerX + Math.cos(angle) * r;
            const y = centerY + Math.sin(angle) * r;
            
            // 标签
            this.ctx.fillStyle = '#333';
            this.ctx.font = 'bold 11px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(dimensions[i], x, y);
            
            // 数据点
            const dataR = (scores[i] / 100) * radius;
            const dataX = centerX + Math.cos(angle) * dataR;
            const dataY = centerY + Math.sin(angle) * dataR;
            
            this.ctx.fillStyle = CHART_COLORS.primary;
            this.ctx.beginPath();
            this.ctx.arc(dataX, dataY, 4, 0, Math.PI * 2);
            this.ctx.fill();
            
            // 分数
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '10px Arial';
            this.ctx.fillText(scores[i].toString(), dataX, dataY);
        }
    }

    drawTitle(text, x, y) {
        this.ctx.fillStyle = '#333';
        this.ctx.font = 'bold 16px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, x, y);
    }
}

// ============================================================
// 初始化全局图表实例
// ============================================================
window.charts = {
    severityPie: new SeverityPieChart('severityChart'),
    priorityBar: new PriorityBarChart('priorityChart'),
    trendLine: new TrendLineChart('trendChart'),
    complianceRadar: new ComplianceRadarChart('complianceRadar')
};
