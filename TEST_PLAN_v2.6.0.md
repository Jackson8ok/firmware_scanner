# AFVS v2.6.0 验收测试计划

**版本**: v2.6.0  
**验收编号**: VAL-AFVS-2026-010  
**日期**: 2026-08-26  
**状态**: 待测试  
**编写人**: 攻城狮阿信 [Jackson]  
**邮箱**: zhu80k@163.com  

---

## 1. 测试范围

| 类别 | 描述 | 验收标准 |
|------|------|----------|
| P0-1 | grype CLI 并发优化 | 扫描速度提升 ≥ 50% |
| P0-2 | 结果缓存机制 | 重复固件命中率 ≥ 80% |
| P1-1 | 自定义报告模板 | 3+ 模板可用 |
| P1-2 | 批量扫描队列 | 支持 10+ 固件并发 |
| P1-3 | 邮件通知模块 | 扫描完成后邮件发送 |
| P1-4 | 前端版本号注入 | `/api/health` 实时同步 |
| P2-1 | 健康检查接口 | 返回正确版本 |

---

## 2. 测试脚本

### 2.1 P0-1: 并发优化测试

```bash
# 单个固件扫描基线
time python3 scan_firmware.py firmware_test.bin

# 批量扫描（3 并发）
time python3 batch_scan.py --concurrent 3 firmware_*.bin

# 验证并发数
ps aux | grep grype | wc -l  # 应显示 3 个并发
```

**预期**: 3 并发扫描耗时 ≤ 单次 1/2 时长

### 2.2 P0-2: 缓存命中测试

```python
from scanner.cache.grype_cache import GrypeCache
cache = GrypeCache()

# 第一次扫描（缓存未命中）
result1 = cache.get_or_scan("firmware.bin")
assert result1 is not None
assert not result1.get("_cached")

# 第二次扫描（缓存命中）
result2 = cache.get_or_scan("firmware.bin")
assert result2.get("_cached") is True
assert result2.get("scan_time", 0) < 1  # 缓存命中 < 1s
```

### 2.3 P1-1: 报告模板测试

```python
from report_generator.template_report import TemplateReportGenerator

gen = TemplateReportGenerator()
templates = gen.list_templates()
assert len(templates) >= 3

for t in templates:
    gen.set_template(t["name"])
    html = gen.generate_html(test_scan_result)
    assert len(html) > 0
    assert "<html" in html
```

### 2.4 P1-2: 批量扫描测试

```python
from scanner.batch_queue import BatchScanQueue

queue = BatchScanQueue(max_concurrent=3)
firmware_list = [{"path": f"/tmp/fw{i}.bin", "type": "auto"} for i in range(10)]
batch_id = queue.add_batch(firmware_list)

status = queue.get_batch_status(batch_id)
assert status["total"] == 10
```

### 2.5 P1-3: 邮件通知测试

```bash
# 发送测试邮件
curl -X POST http://localhost:5000/api/notify/test \
  -H "Content-Type: application/json" \
  -d '{"recipients": ["test@example.com"]}'
```

**预期**: 收到富文本 HTML 邮件（含风险评分卡片）

### 2.6 P1-4: 版本号注入测试

```bash
# 验证 /api/health 返回版本
curl http://localhost:5000/api/health

# 预期：{"version": "2.6.0", ...}
```

---

## 3. 验收清单

### P0: 性能优化 (必选)

| 编号 | 测试项 | 预期 | 实际 | 状态 |
|------|--------|------|------|------|
| P0-1 | grype CLI 并发 | 速度 ↑ ≥ 50% | | ⬜ |
| P0-2 | 缓存命中 | 命中率 ≥ 80% | | ⬜ |
| P0-3 | 并发数控制 | 3 个并发 | | ⬜ |

### P1: 功能增强 (重要)

| 编号 | 测试项 | 预期 | 实际 | 状态 |
|------|--------|------|------|------|
| P1-1 | 6 种模板 | 全部生成 | | ⬜ |
| P1-2 | 批量 10+ 固件 | 并发处理 | | ⬜ |
| P1-3 | 邮件通知 | 收到邮件 | | ⬜ |
| P1-4 | 版本号同步 | /api/health = v2.6.0 | | ⬜ |
| P1-5 | API 端点 | 5000 响应 | | ⬜ |

### P2: 辅助功能 (可选)

| 编号 | 测试项 | 预期 | 实际 | 状态 |
|------|--------|------|------|------|
| P2-1 | WebSocket 推送 | 实时进度 | | ⬜ |
| P2-2 | PDF 导出 | 正常生成 | | ⬜ |
| P2-3 | 响应式 UI | 移动端适配 | | ⬜ |

---

## 4. 测试环境

| 组件 | 版本/配置 |
|------|-----------|
| Python | 3.11 |
| Grype CLI | 0.117.0 |
| Grype DB | v6 |
| Syft | v1.51.0 |
| EPSS | latest |
| Redis | 7.x |
| Flask | 2.3.x |
| Jinja2 | 3.1.x |

---

## 5. 签字

| 角色 | 姓名 | 签字 | 日期 |
|------|------|------|------|
| 测试工程师 | | | |
| 产品经理 | | | |
| 负责人 | 攻城狮阿信 | | 2026-08-26 |

---

**附件**:
- [DEV_LOG_v2.6.0_PHASE3.md](./DEV_LOG_v2.6.0_PHASE3.md)
- [DEV_LOG_v2.6.0_PHASE4.md](./DEV_LOG_v2.6.0_PHASE4.md)
- [DEV_LOG_v2.6.0_PHASE5.md](./DEV_LOG_v2.6.0_PHASE5.md)
- [DEV_LOG_v2.6.0_PHASE6.md](./DEV_LOG_v2.6.0_PHASE6.md)
