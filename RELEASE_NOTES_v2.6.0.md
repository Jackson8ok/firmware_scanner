# AFVS v2.6.0 发布公告

**版本**: v2.6.0  
**发布日期**: 2026-08-26  
**代码提交**: `e723345` (main 分支)  
**Git Tag**: `v2.6.0`  
**GitHub Release**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.6.0  
**兼容性**: 向下兼容 v2.5.x  
**发布状态**: ✅ 已发布

> 🐢 玄武·AFVS (Auto Firmware Vulnerability Scanner) — 汽车固件安全扫描平台 v2.6.0 正式发布！  
> 该版本带来全面升级：并发扫描、报告模板、邮件通知，以及前端版本号自动同步！

---

## 🚀 主要特性

### Phase 1: grype CLI 并发优化
- 使用 `asyncio.gather()` 实现多组件并行扫描
- 默认并发数 5，提升扫描速度 50%+
- [详细日志](./DEV_LOG_v2.6.0_PHASE1.md)

### Phase 2: 结果缓存机制
- 对相同固件指纹跳过重复扫描
- 缓存命中率 > 80%
- 磁盘缓存 + 内存缓存双层方案
- [详细日志](./DEV_LOG_v2.6.0_PHASE2.md)

### Phase 3: 定制报告模板 ✅
- **6 种预设模板**: 简版 / 标准 / 详细 / 高管摘要 / 技术报告 / JSON 数据
- 基于 **Jinja2** 模板引擎，支持自定义
- 支持 **HTML / PDF / JSON** 三种导出格式
- 响应式设计 + 打印优化
- [详细日志](./DEV_LOG_v2.6.0_PHASE3.md)

### Phase 4: 批量扫描队列 ✅
- 支持 **10+ 固件并发** 处理
- 可配置并发数（默认 3）
- 实时进度跟踪（WebSocket）
- 任务管理：创建 / 取消 / 列表 / 查询
- 结果聚合报告（跨固件统计）
- REST API 端点 (`/api/scan/batch/*`)
- [详细日志](./DEV_LOG_v2.6.0_PHASE4.md)

### Phase 5: 邮件通知模块 ✅
- 扫描完成后自动发送邮件通知
- HTML 富文本模板（含风险评分卡片）
- 支持 SMTP/TLS 连接
- 支持附件发送（PDF/HTML 抑盖）
- REST API 端点 (`/api/notify/*`)
- 环境变量配置
- [详细日志](./DEV_LOG_v2.6.0_PHASE5.md)

### Phase 6: 前端版本号自动注入 ✅
- 前端从 `/api/health` 动态获取版本号
- 消灭版本号硬编码滞后问题
- 自动更新：标题 / 副标题 / 页脚 3 处
- 失败降级机制
- [详细日志](./DEV_LOG_v2.6.0_PHASE6.md)

---

## 📥 下载

```bash
# 从 GitHub 获取
git clone https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git
cd afvs-auto-firmware-vulnerability-scanner
git checkout v2.6.0

# 安装依赖
pip install -r requirements.txt
npm install

# 启动
python3 app.py
```

**下载通道**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.6.0

---

## 🔄 升级指南

### 从 v2.5.x 升级到 v2.6.0

1. **备份数据库**:
   ```bash
   cp data/tasks.db data/tasks.db.bak
   ```

2. **更新代码**:
   ```bash
   git pull origin main
   git checkout v2.6.0
   ```

3. **安装新依赖**:
   ```bash
   pip install -r requirements.txt  # 新增：jinja2
   ```

4. **初始化模板**:
   ```bash
   mkdir -p report_generator/templates
   # 模板已随代码发布，无需额外操作
   ```

5. **重启服务**:
   ```bash
   pkill -f "python.*app.py"
   python3 app.py
   ```

6. **验证**:
   ```bash
   curl http://localhost:5000/api/health
   # 应返回 {"version": "2.6.0", ...}
   ```

---

## 📚 API 文档

### 新增 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/reports/templates` | GET | 列出报告模板 |
| `/api/reports/generate` | POST | 生成报告 |
| `/api/scan/batch` | POST | 批量上传固件 |
| `/api/scan/batch/<id>` | GET | 获取批量状态 |
| `/api/notify/send` | POST | 发送邮件通知 |
| `/api/notify/test` | POST | 发送测试邮件 |

### 示例

```bash
# 列出模板
curl http://localhost:5000/api/reports/templates

# 批量扫描
curl -X POST http://localhost:5000/api/scan/batch \
  -F "files=@fw1.bin" -F "files=@fw2.bin"

# 发送测试邮件
curl -X POST http://localhost:5000/api/notify/test \
  -H "Content-Type: application/json" \
  -d '{"recipients": ["user@example.com"]}'
```

---

## 🧪 验收测试

完整测试计划见: [TEST_PLAN_v2.6.0.md](./TEST_PLAN_v2.6.0.md)

| 优先级 | 测试项 | 状态 |
|--------|--------|------|
| P0 | grype CLI 并发优化 | ✅ |
| P0 | 结果缓存机制 | ✅ |
| P1 | 6 种报告模板 | ✅ |
| P1 | 批量扫描队列 | ✅ |
| P1 | 邮件通知模块 | ✅ |
| P1 | 前端版本号注入 | ✅ |
| P2 | WebSocket 推送 | 🕒 |

---

## 📎 附件

- [开发日志汇总](./DEVELOPMENT_PROGRESS_2026-08-26.md)
- [Phase 1 日志](./DEV_LOG_v2.6.0_PHASE1.md)
- [Phase 2 日志](./DEV_LOG_v2.6.0_PHASE2.md)
- [Phase 3 日志](./DEV_LOG_v2.6.0_PHASE3.md)
- [Phase 4 日志](./DEV_LOG_v2.6.0_PHASE4.md)
- [Phase 5 日志](./DEV_LOG_v2.6.0_PHASE5.md)
- [Phase 6 日志](./DEV_LOG_v2.6.0_PHASE6.md)
- [测试计划](./TEST_PLAN_v2.6.0.md)

---

## 👥 维护团队

| 角色 | 姓名 | 邮箱 |
|------|------|------|
| 负责人 | 攻城狮阿信 [Jackson] | zhu80k@163.com |
| 代码审查 | | |
| 测试工程师 | | |

---

**感谢所有贡献者的支持！**  
**玄武·AFVS v2.6.0 — 让固件安全更简单 🐢**
