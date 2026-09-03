# AFVS v2.7.1 发布说明

**版本**: v2.7.1-hotfix  
**发布日期**: 2026-09-03  
**维护者**: 攻城狮阿信 [Jackson]  
**验收编号**: VAL-AFVS-2026-015（计划中）

---

## 🎯 版本定位

**v2.7.1 是 v2.7.0 的质量修复版**，专注于解决验收方提出的 4 项低优先级问题，提升产品的生产就绪度。

---

## 📋 修复内容

### 问题 1: 版本号未更新 ✅

**问题描述**: `/api/health` 端点返回版本号 "2.6.0"，应为 "2.7.1"

**影响**: 
- 用户无法通过 API 获取正确版本号
- 版本管理混乱

**修复方案**:
- 在 `config.yaml` 中添加 `app.version: "2.7.1"`
- 从配置文件读取版本号，避免硬编码
- 健康检查端点动态返回配置版本

**修改文件**:
- `config.yaml` - 新增 `app.version` 配置项
- `api/main.py` - 从配置读取版本号（第 166 行、309 行）

**验证方法**:
```bash
curl http://localhost:8765/api/health
# 应返回：{"version": "2.7.1", ...}
```

---

### 问题 2: 参数命名误导 ✅

**问题描述**: `POST /api/sbom/import` 的参数 `firmware_id` 实际语义是扫描任务 ID，命名误导

**影响**:
- API 使用者容易误解参数含义
- 首次调用可能失败

**修复方案**:
- 添加新参数 `task_id`（推荐）
- 保留旧参数 `firmware_id`（向后兼容）
- 添加弃用警告日志

**修改文件**:
- `services/sbom/sbom_api.py` - 第 157-165 行

**API 变更**:
```python
# v2.7.0（旧）
POST /api/sbom/import
  - firmware_id: "关联的固件 ID"

# v2.7.1（新）
POST /api/sbom/import
  - task_id: "关联的扫描任务 ID" (推荐)
  - firmware_id: "[已弃用] 使用 task_id 代替" (向后兼容)
```

**验证方法**:
```bash
# 新方式（推荐）
curl -X POST http://localhost:8765/api/sbom/import \
  -F "file=@sbom.json" \
  -F "task_id=task_123"

# 旧方式（仍可用，但会打印警告）
curl -X POST http://localhost:8765/api/sbom/import \
  -F "file=@sbom.json" \
  -F "firmware_id=task_123"
```

---

### 问题 3: SBOM 存储路径硬编码 ✅

**问题描述**: SBOM 上传目录硬编码为 `/mnt/workspace/firmware_scanner/uploads/sbom`，Windows 下会创建异常目录

**影响**:
- Windows 用户无法正常使用
- 路径不可配置

**修复方案**:
- 使用配置项 `paths.sbom_uploads`
- 支持环境变量占位符 `${SBOM_UPLOAD_DIR:-./uploads/sbom}`
- 实现 `resolve_path()` 函数解析路径

**修改文件**:
- `config.yaml` - 新增 `paths.sbom_uploads` 配置项
- `services/sbom/sbom_api.py` - 第 137-161 行

**配置示例**:
```yaml
# config.yaml
paths:
  sbom_uploads: "${SBOM_UPLOAD_DIR:-./uploads/sbom}"
```

```bash
# Linux/macOS
export SBOM_UPLOAD_DIR=/mnt/workspace/firmware_scanner/uploads/sbom

# Windows (PowerShell)
$env:SBOM_UPLOAD_DIR="C:\firmware_scanner\uploads\sbom"
```

**验证方法**:
```bash
# 检查日志
INFO:services.sbom.sbom_api:SBOM 上传目录：/mnt/workspace/firmware_scanner/uploads/sbom
```

---

### 问题 4: SBOM 存储为内存字典 ✅

**问题描述**: SBOM 数据存储在内存字典 `_sbom_store` 中，进程重启后数据丢失

**影响**:
- 服务重启后所有 SBOM 记录丢失
- 无法用于生产环境

**修复方案**:
- 创建 `SBOMDatabase` 类封装 SQLite 操作
- 实现 `save()`, `get()`, `delete()`, `list_all()` 方法
- 使用 JSON 格式存储组件数据

**修改文件**:
- `services/sbom/sbom_api.py` - 第 46-134 行

**数据库结构**:
```sql
CREATE TABLE IF NOT EXISTS sbom_records (
    sbom_id TEXT PRIMARY KEY,
    file_path TEXT,
    task_id TEXT,
    components JSON,
    components_count INTEGER,
    format TEXT,
    created_at TEXT,
    status TEXT
);
```

**验证方法**:
```python
# 测试持久化
from services.sbom.sbom_api import sbom_db

# 保存
sbom_db.save({...})

# 读取（重启后仍可用）
data = sbom_db.get('sbom_xxx')
```

---

## 📊 技术变更汇总

| 类别 | 变更内容 | 文件数 | 行数变化 |
|------|---------|--------|---------|
| **配置管理** | 新增 `app.version`, `paths.sbom_uploads`, `paths.sbom_db` | 1 | +10 |
| **API 端点** | 参数命名优化（向后兼容） | 1 | +8 |
| **数据持久化** | SQLite 数据库实现 | 1 | +95 |
| **路径解析** | 支持环境变量占位符 | 1 | +25 |
| **总计** | - | 2 | **+138 行** |

---

## ✅ 验收标准

| 标准 | 要求 | 实测 | 状态 |
|------|------|------|:--:|
| 版本号正确 | `/api/health` 返回 "2.7.1" | ✅ 通过 | ✅ |
| 参数向后兼容 | `firmware_id` 仍可用 | ✅ 通过 | ✅ |
| 路径可配置 | 支持环境变量覆盖 | ✅ 通过 | ✅ |
| 数据持久化 | 重启后数据不丢失 | ✅ 通过 | ✅ |
| 语法检查 | `py_compile` 通过 | ✅ 通过 | ✅ |
| 模块导入 | 无 ImportError | ✅ 通过 | ✅ |
| CRUD 测试 | 保存/读取/删除正常 | ✅ 通过 | ✅ |

---

## 📝 已知问题

| 问题 | 影响 |  workaround | 计划修复版本 |
|------|------|-------------|-------------|
| 无 | - | - | - |

---

## 🔗 相关资源

| 资源 | 链接 |
|------|------|
| **GitHub Release** | https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.1 |
| **开发日志** | DEV_LOG_v2.7.1_HOTFIX.md |
| **验收报告** | （待创建）VAL-AFVS-2026-015 |
| **上一版本** | v2.7.0 - 组件指纹识别增强版 |

---

## 📞 联系方式

**维护者**: 攻城狮阿信 [Jackson]  
**邮箱**: zhu80k@163.com  
**GitHub**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner

---

**结论**: v2.7.1-hotfix 完成 4 项低优先级问题修复，提升生产就绪度，建议所有 v2.7.0 用户升级。

⟦ v2.7.1 发布说明创建完成｜4 项修复全部完成并验证通过；下一步：推送代码 + 创建 Release｜锚点：v2.7.1-hotfix, 4 项修复，VAL-AFVS-2026-015 ⟧
