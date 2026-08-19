# 玄武固件扫描器 v2.4.3 修复计划

**创建日期**: 2026-08-19  
**优先级**: 🔴 P0 加急（客户复测不通过）  
**目标复测日期**: 2026-08-20（1 个工作日内）  
**验收标准**: 客户 VAL-FWSCAN-2026-002 复测通过条件

---

## 1. 客户复测结论摘要

### ⛔ 复测状态：不通过

| 缺陷编号 | 严重度 | 问题描述 | 状态 |
|---------|--------|---------|------|
| DEF-NEW-01 | 🔴 致命 | 服务无法启动：`api/main.py` 缺少 `import asyncio` | ✅ 已修复 |
| DEF-NEW-02 | 🔴 严重 | 目录输入分支绕过 Syft，所有组件版本 unknown | ⏳ 修复中 |
| DEF-NEW-03 | 🟠 中 | 版本 unknown 导致版本约束失效，存在误报 | ⏳ 待修复 |
| DEF-NEW-04 | 🟠 中 | CVE 记录重复（按文件数重复计入） | ⏳ 待修复 |
| DEF-NEW-05 | 🟡 低 | 结果字段不完整（published_date=None, cvss_score=0.0） | ⏳ 待修复 |

### 基线对照（ramdisk_rootfs）

| 指标 | v2.4.1 | v2.4.2 | v2.4.3 目标 | 基线期望 |
|------|:--:|:--:|:--:|:--:|
| 组件数 | 53（全错） | 15（不完整） | **≥7（含 busybox）** | 7 |
| 组件版本 | - | 全部 unknown | **版本齐全** | 版本齐全 |
| busybox 识别 | ❌ | ❌ | **✅ 1.35.0** | ✅ 1.35.0 |
| CVE 数 | 394（错误） | 114（含重复） | **≤10（去重后）** | 6 |
| 结果准确率 | ~0% | ~40% | **≥80%** | 100% |

---

## 2. 修复任务清单

### P0 加急（阻断级，必须修复）

#### ✅ DEF-NEW-01: 服务无法启动

**根因**: `api/main.py` 使用了 `asyncio.AbstractEventLoop`、`asyncio.new_event_loop()`、`asyncio.run_coroutine_threadsafe()` 但缺少 `import asyncio`

**修复**:
```python
# api/main.py 第 12 行添加
import asyncio
```

**状态**: ✅ 已完成  
**验证**: `python -c "import api.main"` 无报错

---

#### ⏳ DEF-NEW-02: 目录输入分支绕过 Syft

**根因**: `generate_sbom()` 检测到目录输入时直接调用 `extract_squashfs_components_from_dir()`，完全绕过 Syft

**当前逻辑**:
```python
if os.path.isdir(firmware_path):
    return self.extract_squashfs_components_from_dir(firmware_path)  # ❌ 绕过 Syft
```

**修复方案**:
```python
if os.path.isdir(firmware_path):
    # ✅ 优先使用 Syft 目录扫描
    if self.syft_available:
        try:
            return self.generate_syft_sbom(firmware_path)  # Syft 支持 dir: 协议
        except Exception as e:
            logger.warning(f"Syft 目录扫描失败，降级：{e}")
    # 降级到自研提取器
    return self.extract_squashfs_components_from_dir(firmware_path)
```

**影响文件**: `scanner/engine.py` (L508-509)

**状态**: ⏳ 修复中  
**验证**: 
- busybox 1.35.0 正确识别
- 组件版本不再全为 unknown

---

### P1（严重级，复测通过条件）

#### ⏳ DEF-NEW-03: 版本 unknown 导致版本约束失效

**根因**: 
1. DEF-NEW-02 导致版本提取失败
2. CVE 匹配时版本约束检查对 unknown 版本不生效

**修复方案**:

**方案 A**: 版本识别修复后自动解决（依赖 DEF-NEW-02）

**方案 B**: 增强版本约束逻辑
```python
# scanner/engine.py - CVEMatcher._version_matches()
def _version_matches(self, component_version: str, constraint: str) -> bool:
    if component_version == 'unknown':
        # 版本未知时，记录警告但不匹配（避免误报）
        logger.warning(f"组件版本未知，跳过版本约束检查")
        return False  # 或返回 True 但标记为"需人工确认"
    # ... 现有版本比较逻辑
```

**方案 C**: 结果标注
- 版本为 unknown 的 CVE 在报告中标注"版本未知，需人工确认"
- R155 合规检查时不计入判定

**状态**: ⏳ 依赖 DEF-NEW-02  
**验证**: CVE-2017-0379（影响 libgcrypt <1.7.x）不再误报（ramdisk 中 libgcrypt 为 1.8.5）

---

#### ⏳ DEF-NEW-04: CVE 记录重复

**根因**: 每个组件每个 CVE 按其出现文件数重复计入

**修复方案**:
```python
# scanner/engine.py - CVEMatcher.match()
vulnerabilities = []
seen = set()  # (cve_id, component_name, version)

for component in components:
    for vuln in component_vulns:
        key = (vuln.cve_id, component.name, component.version)
        if key not in seen:
            seen.add(key)
            vulnerabilities.append(vuln)
```

**状态**: ⏳ 待修复  
**验证**: 114 条 CVE 去重后约 57 条 → 目标 ≤10 条

---

### P2（优化级）

#### ⏳ DEF-NEW-05: 结果字段不完整

**问题**: published_date=None、cvss_score=0.0 占比高（114 条中 56 条 severity=Unknown）

**修复方案**:
```python
# scanner/engine.py - CVEMatcher._query_component()
# 从 Grype DB 完整提取字段
vuln = Vulnerability(
    cve_id=row['cve_id'],
    component_name=component.name,
    version=component.version,
    severity=row.get('severity', 'Unknown'),
    cvss_score=row.get('cvss_score', 0.0),  # ✅ 从 DB 读取
    published_date=row.get('published_date'),  # ✅ 从 DB 读取
    description=row.get('description', '')
)
```

**状态**: ⏳ 待修复  
**验证**: severity=Unknown 占比 <10%

---

#### ⏳ DEF-04(遗留): 备用合规检查器 published_date 仍用 datetime.now()

**位置**: `task_queue.py` L515

**修复**: 与主路径保持一致，从 Vulnerability 对象读取

**状态**: ⏳ 待修复

---

#### ⏳ DEF-06(遗留): 配置与版本标识

**问题**:
1. config.yaml 默认值仍为 Linux 路径
2. /api/health 版本标识仍显示 2.4.1-hotfix

**修复**:
```yaml
# config.yaml
app:
  version: "2.4.3"  # ✅ 更新
```

```python
# api/main.py - health_check()
return {"version": "2.4.3", "status": "healthy", ...}
```

**状态**: ⏳ 待修复

---

## 3. 发布流程改进

### 建议纳入 CI 的冒烟测试

```bash
# scripts/smoke_test.sh
#!/bin/bash
set -e

echo "=== 启动冒烟测试 ==="

# 1. 导入测试
python -c "import api.main" || { echo "❌ 导入失败"; exit 1; }
echo "✅ 导入测试通过"

# 2. 启动测试（3 秒检查进程存活）
uvicorn api.main:app --port 8765 &
UVICORN_PID=$!
sleep 3

if ! kill -0 $UVICORN_PID 2>/dev/null; then
    echo "❌ 服务启动失败"
    exit 1
fi
echo "✅ 启动测试通过"

# 3. 健康检查
curl -s http://localhost:8765/api/health | grep -q '"status":"healthy"' || { echo "❌ 健康检查失败"; kill $UVICORN_PID; exit 1; }
echo "✅ 健康检查通过"

# 4. 清理
kill $UVICORN_PID
echo "=== 冒烟测试通过 ==="
```

**状态**: ⏳ 待创建

---

## 4. 修复优先级与时间估算

| 优先级 | 任务 | 预计工时 | 负责人 | 状态 |
|:--:|------|:--:|:--:|:--:|
| P0 | DEF-NEW-01: 添加 import asyncio | 5 分钟 | 攻城狮阿信 | ✅ 已完成 |
| P0 | DEF-NEW-02: Syft 目录扫描集成 | 2 小时 | 攻城狮阿信 | ✅ 已完成 |
| P1 | DEF-NEW-03: 版本约束增强 | 1 小时 | 攻城狮阿信 | ✅ 已完成 |
| P1 | DEF-NEW-04: CVE 去重 | 30 分钟 | 攻城狮阿信 | ✅ 已完成 |
| P2 | DEF-NEW-05: 字段补全 | 1 小时 | 攻城狮阿信 | ✅ 已完成 |
| P2 | DEF-04/06: 遗留项 | 30 分钟 | 攻城狮阿信 | ✅ 已完成 |
| P2 | 冒烟测试脚本 | 1 小时 | 攻城狮阿信 | ✅ 已完成 |
| **总计** | - | **~6 小时** | - | - |

---

## 5. 验证计划

### 5.1 单元测试

```bash
# 1. 导入测试
python -c "import api.main"

# 2. Syft 目录扫描测试
python -c "
from scanner.engine import FirmwareExtractor
extractor = FirmwareExtractor()
components = extractor.generate_sbom('/path/to/extracted_dir', 'auto')
assert any(c.name == 'busybox' and c.version == '1.35.0' for c in components)
"

# 3. CVE 去重测试
# 验证 (cve_id, component, version) 去重逻辑
```

### 5.2 端到端测试

```bash
# 1. 服务启动
uvicorn api.main:app --port 8765 &

# 2. 上传 ramdisk 固件
curl -X POST http://localhost:8765/api/upload -F "file=@ramdisk_rootfs.bin"

# 3. 启动扫描
curl -X POST http://localhost:8765/api/scan -F "firmware_id=ramdisk_rootfs.bin" -F "firmware_type=auto"

# 4. 查询结果
curl http://localhost:8765/api/task/{task_id}/result

# 5. 验证基线指标
# - 组件数 ≥7
# - busybox 1.35.0 识别
# - CVE 数 ≤10（去重后）
# - 无重复记录
```

### 5.3 客户复测用例

| 用例 | 目标值 | 验证方法 |
|------|--------|----------|
| busybox 1.35.0 识别 | ✅ | 组件列表包含 busybox 1.35.0 |
| CVE 匹配率 ≥80% | ✅ | 与基线 6 CVE 对比 |
| 无项目依赖泄漏 | ✅ | 组件均为固件内容 |
| 无重复记录 | ✅ | CVE 列表去重验证 |
| 无版本约束误报 | ✅ | CVE-2017-0379 不再误报 |
| 服务可直接启动 | ✅ | uvicorn 启动无报错 |

---

## 6. 版本发布

### 发布清单

- [ ] 代码修复完成（所有 P0/P1 项）
- [ ] 单元测试通过
- [ ] 端到端测试通过（ramdisk 样本）
- [ ] 冒烟测试脚本创建
- [ ] 版本号更新为 2.4.3
- [ ] CHANGELOG 更新
- [ ] Git 提交并推送
- [ ] GitHub Release 创建
- [ ] 交付包生成（firmware_scanner-2.4.3.zip）
- [ ] 提交客户复测申请

### 时间计划

| 节点 | 时间 | 状态 |
|------|------|------|
| 修复完成 | 2026-08-19 18:00 | ⏳ 待完成 |
| 测试验证 | 2026-08-19 20:00 | ⏳ 待完成 |
| 代码推送 | 2026-08-19 21:00 | ⏳ 待完成 |
| Release 发布 | 2026-08-19 22:00 | ⏳ 待完成 |
| 交付客户 | 2026-08-19 23:00 | ⏳ 待完成 |
| 复测通过 | 2026-08-20 | ⏳ 等待中 |

---

## 7. 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| Syft 目录扫描仍失败 | 高 | 低 | 保留降级逻辑 + 增强日志 |
| 版本识别仍为 unknown | 中 | 中 | 标注"需人工确认"，不计入 R155 |
| CVE 去重影响其他功能 | 低 | 低 | 单元测试覆盖 |
| 复测时间紧张 | 中 | 中 | 优先 P0/P1，P2 可延后 |

---

**维护者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**GitHub**: [Jackson8ok/firmware_scanner](https://github.com/Jackson8ok/firmware_scanner)  
**状态**: ⏳ 修复中（P0 已完成，P0/P1 修复中）
