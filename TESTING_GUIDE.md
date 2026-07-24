# 🧪 固件漏洞扫描平台 - 测试指南

## ✅ 快速测试流程

### 1. 检查服务状态

```bash
# 查看是否有 uvicorn 进程
ps aux | grep uvicorn

# 检查端口是否监听
netstat -tlnp | grep 8000

# 测试健康检查
curl http://localhost:8000/health
```

**预期输出**: `{"status":"ok","timestamp":"..."}`

---

### 2. 访问 Web 界面

打开浏览器访问：**http://localhost:8000**

应该看到:
- ✅ 首页标题"🦞 固件漏洞扫描平台"
- ✅ 两个扫描表单（单个文件/批量扫描）
- ✅ 任务队列状态面板
- ✅ 筛选控制面板

---

### 3. 测试 R155 合规功能

#### 方法 A: 上传测试固件（推荐）

**步骤**:

1. 打开 http://localhost:8000
2. 选择"单个文件扫描"
3. 上传一个测试固件文件（如果有的话）
4. 等待扫描完成
5. **查看结果**：
   - 总 CVE 数量卡片
   - **R155 合规评分卡片**（紫色渐变背景）
   - "合规详情"选项卡（如果有违规）

**如果没有真实固件，可以创建模拟数据测试 UI**:

```python
# 创建测试数据
cat > /tmp/test_r155_data.py << 'EOF'
import json

test_data = {
    "firmware_id": "test-123",
    "filename": "test.bin",
    "total_cves": 2,
    "critical_count": 1,
    "high_count": 1,
    "r155_compliance": {
        "compliance_score": 65.5,
        "violating_cves": 1,
        "violations": [
            {
                "rule_id": "CM.01",
                "cve_id": "CVE-2021-44228",
                "component": "Apache Log4j",
                "penalty_score": 8.5,
                "remediation": "升级到 2.17.0 或更高版本"
            }
        ],
        "category_scores": {
            "Supply Chain Security": 72.5,
            "Vulnerability Management": 68.0,
            "Authentication & Access Control": 55.0
        },
        "recommendations": [
            "🔴 优先处理'Supply Chain Security'类别的问题",
            "⚠️ 发现 1 个严重合规违规，需要紧急修复"
        ]
    }
}

print(json.dumps(test_data, indent=2))
EOF
python3 /tmp/test_r155_data.py
```

#### 方法 B: API 直接测试

```bash
# 获取任务列表（应该有历史扫描）
curl http://localhost:8000/api/tasks?limit=5 | python3 -m json.tool

# 如果有完成任务，获取其合规报告
TASK_ID="你的任务 ID"
curl http://localhost:8000/api/compliance/$TASK_ID | python3 -m json.tool

# 查看类别得分
curl http://localhost:8000/api/compliance/categories/$TASK_ID | python3 -m json.tool
```

---

### 4. 前端功能验证

打开浏览器开发者工具 (F12)，检查以下内容:

#### Console 标签页
- ✅ 没有 JavaScript 错误
- ✅ 看到 "🔒 R155 合规报告模块已加载"

#### Network 标签页
- ✅ 请求 `/api/task/{id}` 返回正确数据
- ✅ 看到 `r155_compliance` 字段在响应中

#### Elements 标签页
- ✅ 存在 `<div id="complianceScore">` 元素
- ✅ 存在 `<div id="r155TabsSection">` 选项卡结构
- ✅ R155 卡片显示在 statsGrid 中

---

## 📋 完整功能检查清单

### 后端功能

| 功能 | 命令 | 预期结果 |
|------|------|---------|
| 健康检查 | `curl http://localhost:8000/health` | `{"status":"ok"}` |
| 上传文件 | POST to `/api/upload` | 返回 task_id |
| 查询任务 | GET `/api/task/{id}` | 包含 status, progress |
| 获取结果 | GET `/api/task/{id}` (完成后) | 包含 vulnerabilities |
| **R155 报告** | **GET `/api/compliance/{id}`** | **包含 compliance_score** |
| **类别得分** | **GET `/api/compliance/categories/{id}`** | **包含 category_scores** |

### 前端功能

| 功能 | 操作 | 预期结果 |
|------|------|---------|
| 页面加载 | 访问 http://localhost:8000 | 显示完整界面 |
| 上传文件 | 选择文件并提交 | 显示上传进度 |
| 查看结果 | 扫描完成后 | 显示统计数据 |
| **R155 卡片** | **有漏洞时** | **显示合规评分** |
| **选项卡切换** | **点击合规选项卡** | **内容切换正常** |
| **图表渲染** | **切换到类别得分** | **饼图/雷达图显示** |

---

## 🐛 常见问题排查

### Q1: 服务无法启动

**症状**: `uvicorn` 进程不启动或立即退出

**解决**:
```bash
# 查看详细错误
cd /mnt/workspace/firmware_scanner
python3 -c "from api.main import app; print('Import OK')"

# 检查配置文件
python3 -c "import yaml; print(yaml.safe_load(open('config.yaml')))"

# 手动启动并查看日志
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Q2: R155 卡片不显示

**症状**: 扫描完成但看不到 R155 评分卡片

**原因**: 
- 没有触发合规检查
- 前端 JS 加载失败
- 数据格式不匹配

**解决**:
```javascript
// 在浏览器 Console 执行
console.log(window.currentComplianceData); // 应该有数据
window.updateComplianceStats({compliance_score: 80}); // 手动测试
```

### Q3: 选项卡无法切换

**症状**: 点击选项卡无反应

**解决**:
```javascript
// 检查函数是否存在
typeof switchTab  // 应返回 "function"

// 手动调用
switchTab('compliance-details')
```

### Q4: 图表不显示

**症状**: 类别得分区域空白

**解决**:
```javascript
// 检查 Chart.js 是否加载
typeof Chart  // 应返回 "function"

// 查看控制台是否有渲染错误
// F12 -> Console
```

---

## 🎯 自动化测试脚本

运行我们创建的测试脚本:

```bash
cd /mnt/workspace/firmware_scanner
./scripts/test_r155.sh
```

这将自动:
1. 检查服务是否运行
2. 验证所有 API 端点
3. 尝试获取现有任务的合规报告
4. 显示测试结果摘要

---

## 📊 性能测试

### 并发测试

```bash
# 同时启动 5 个扫描任务
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/batch-upload \
    -F "files=@/path/to/firmware$i.bin" \
    -F "firmware_type=squashfs" &
done
wait
echo "所有任务已提交"
```

### 压力测试

使用 Apache Bench 或 wrk 测试 API 性能:

```bash
# 需要安装 ab
ab -n 100 -c 10 http://localhost:8000/health
```

---

## 🔍 调试技巧

### 启用详细日志

编辑 `config.yaml`:

```yaml
server:
  debug: true  # 添加这一行
```

然后重启服务。

### 查看数据库内容

```bash
sqlite3 data/vulndb.sqlite << 'EOF'
.mode column
.headers on
SELECT task_id, status, progress FROM scan_tasks ORDER BY created_at DESC LIMIT 5;
EOF
```

### 追踪 JavaScript 错误

```javascript
// 在浏览器 Console
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Error:', msg, 'at', lineNo);
    return false;
};
```

---

## ✅ 测试完成标准

当您能够成功完成以下所有操作时，测试即通过:

- [x] 服务正常启动并在 8000 端口监听
- [x] 能够访问 http://localhost:8000 看到完整界面
- [x] 上传一个测试文件并开始扫描
- [x] 看到实时的进度更新
- [x] 扫描完成后能看到详细的漏洞列表
- [x] **R155 合规评分卡片正确显示**
- [x] **点击合规选项卡能正常切换内容**
- [x] **违规详情表格填充了数据**
- [x] **类别得分图表（饼图/雷达图）正常渲染**
- [x] **改进建议列表正常显示**
- [x] API 端点 `/api/compliance/{id}` 返回正确的 JSON 数据
- [x] 没有 JavaScript 错误或网络错误

---

## 📝 测试报告模板

测试完成后，记录以下内容:

```markdown
## 测试日期：YYYY-MM-DD

### 环境
- OS: 
- Python: 
- Browser: 

### 测试结果
✅ 服务启动：成功/失败
✅ Web 界面：成功/失败  
✅ R155 卡片：成功/失败
✅ 选项卡切换：成功/失败
✅ 图表渲染：成功/失败

### 发现的问题
1. 
2. 

### 截图
- [ ] 首页截图
- [ ] 扫描结果截图  
- [ ] R155 合规详情截图
```

---

祝您测试顺利！如有问题请参考本文档或查看 `DEPLOYMENT.md` 的故障排查部分。
