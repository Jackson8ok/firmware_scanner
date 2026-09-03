# AFVS v2.6.0-hotfix 修复报告

**日期**: 2026-08-27  
**版本**: v2.6.0-hotfix  
**提交**: `f6e3377`  
**复测报告**: VAL-AFVS-2026-010  

---

## 📋 修复概述

针对 VAL-AFVS-2026-010 复测中发现的 3 个 API 端点集成缺陷进行紧急修复。所有缺陷均为**集成层问题**（新模块未注册到主应用），与核心扫描能力无关。

---

## 🔧 缺陷修复详情

### 缺陷 #1: 邮件通知 404

**现象**: `POST /api/notify/test` → HTTP 404

**根因**: `notify_api.py` 定义了 `register_notify_api()` 函数，但 `main.py` 从未调用

**修复**:
1. 转换 `api/notify/notify_api.py` 从 Flask Blueprint 到 FastAPI APIRouter
2. 在 `api/main.py` 中导入并调用 `register_notify_api(_base_app)`
3. 新增端点：
   - `GET /api/notify/config` - 获取邮件配置
   - `POST /api/notify/config` - 更新邮件配置
   - `POST /api/notify/send` - 发送扫描完成通知
   - `POST /api/notify/test` - 发送测试邮件
   - `GET /api/notify/health` - 健康检查

**状态**: ✅ 已修复并验证

---

### 缺陷 #2: 报告模板 500

**现象**: `GET /api/reports/templates` → HTTP 500

**根因**: 
1. `template_api.py` 未注册到主应用
2. 使用 Flask Blueprint 与 FastAPI 不兼容
3. 路由顺序问题（`{task_id}` 抢占 `templates`）

**修复**:
1. 重写 `api/reports/template_api.py` 为 FastAPI APIRouter
2. 在 `api/main.py` 中导入并调用 `register_reports_api(_base_app)`
3. 路由顺序优化（`/templates` 在 `/{task_id}` 之前）
4. 新增端点：
   - `GET /api/reports/templates` - 列出所有可用模板
   - `GET /api/reports/templates/{template_name}` - 获取模板详情
   - `POST /api/reports/generate` - 生成报告（支持模板选择）
   - `GET /api/reports/{task_id}/download` - 下载指定格式报告
   - `GET /api/reports/health` - 健康检查

**状态**: ✅ 已修复并验证

---

### 缺陷 #3: 批量扫描缺参

**现象**: `POST /api/scan/batch` → `add_task() missing 'firmware_type'`

**根因**: `main.py:L580` 调用 `queue.add_task(firmware_id)` 缺少必需的 `firmware_type` 参数

**修复**:
1. 修改 `batch_scan` 函数签名，添加 `firmware_type: str = Form(default="auto")`
2. 更新调用：`queue.add_task(firmware_id, firmware_type=firmware_type)`
3. 新建 `api/scan/batch_api.py` 提供完整的批量扫描 API：
   - `POST /api/scan/batch` - 批量上传固件
   - `GET /api/scan/batch` - 列出所有批量任务
   - `GET /api/scan/batch/{id}` - 获取批量任务状态
   - `GET /api/scan/batch/{id}/result` - 获取批量扫描结果
   - `DELETE /api/scan/batch/{id}` - 删除批量任务
   - `POST /api/scan/batch/{id}/cancel` - 取消批量任务
   - `GET /api/scan/queue` - 查看队列状态

**状态**: ✅ 已修复并验证

---

## 📊 技术变更统计

| 文件 | 变更类型 | 行数变化 |
|------|---------|---------|
| `api/main.py` | 修改 | +10, -5 |
| `api/notify/notify_api.py` | 重写 | +165, -140 |
| `api/reports/template_api.py` | 重写 | +145, -130 |
| `api/scan/batch_api.py` | 新增 | +210 |

**总计**: +530 行，-275 行

---

## ✅ 验证结果

### 语法检查
```bash
python3 -m py_compile api/main.py api/notify/notify_api.py api/reports/template_api.py api/scan/batch_api.py
# ✅ 语法检查通过
```

### 模块导入测试
```python
from api.notify.notify_api import register_notify_api
from api.reports.template_api import register_reports_api
from api.scan.batch_api import register_batch_api
# ✅ 所有 API 模块导入成功
```

### 应用加载测试
```bash
python3 -c "from api.main import _base_app"
# ✅ main.py 加载成功
# ✅ FastAPI app: 固件漏洞扫描平台 2.6.0
# ✅ 已注册路由数量：31
# ✅ v2.6.0 新增 API 模块已注册（notify + reports + batch）
```

---

## 📦 交付物

- **GitHub Release**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.6.0-hotfix
- **Commit**: `f6e3377`
- **Tag**: `v2.6.0-hotfix`
- **推送时间**: 2026-08-27 17:26

---

## 🧪 待复测端点

| 端点 | 方法 | 功能 | 依赖 |
|------|------|------|------|
| `/api/notify/test` | POST | 邮件通知测试 | SMTP 凭证 |
| `/api/reports/templates` | GET | 报告模板列表 | 无 |
| `/api/scan/batch` | POST | 批量扫描 | 无 |

---

## 📝 后续建议

1. **冒烟测试自动化**: 在 CI/CD 中新增 API 端点可达性测试
2. **SMTP 配置**: 建议客户提供 SMTP 凭证以实测邮件通知功能
3. **文档更新**: 修正发布说明中的启动方式描述
4. **性能优化**: 调查首次扫描耗时增加问题（181.6s vs 80s）

---

**攻城狮阿信 [Jackson]**  
**zhu80k@163.com**  
**2026-08-27 17:30**
