# AFVS v2.7.2 发布说明

**版本**: v2.7.2  
**发布日期**: 2026-09-03  
**维护者**: 攻城狮阿信 [Jackson]  
**验收编号**: VAL-FWSCAN-2026-015

---

## 🎯 版本定位

**v2.7.2 是 Phase 4 完整集成版**，将 v2.7.0 开发的 SBOM 融合架构正式接入 API，使用户能够通过 REST API 使用融合分析功能。

---

## 📋 核心功能

### Phase 4: SBOM 融合架构 API 集成

#### 1. `/api/scan` 支持 `sbom_id` 参数

**新增参数**:
```python
sbom_id: Optional[str] = Form(None, description="可选：SBOM ID 用于融合分析（Phase 4）")
```

**使用示例**:
```bash
curl -X POST http://localhost:8765/api/scan \
  -F "firmware_id=fw_001" \
  -F "firmware_type=bin" \
  -F "sbom_id=sbom_xxx"
```

**返回结果增强**:
```json
{
  "success": true,
  "task_id": "xxx",
  "sbom_enabled": true,
  "message": "扫描任务已提交 (SBOM 融合分析)"
}
```

#### 2. 扫描流程集成融合引擎

**执行阶段**:
- 阶段 1: 解包固件 (进度 0-30%)
- 阶段 2: 生成 SBOM (进度 30-60%)
- 阶段 3: CVE 匹配 (进度 60-90%)
- **阶段 4: SBOM 融合分析 (进度 90-95%)** ← 新增
- 阶段 5: 汇总结果 (进度 95-100%)

**融合逻辑**:
```python
if sbom_id:
    # 1. 获取 SBOM 记录
    sbom_record = sbom_db.get(sbom_id)
    
    # 2. 创建融合引擎
    fusion_engine = SBOMFusionEngine()
    
    # 3. 执行融合分析
    fused_components = fusion_engine.fuse(sbom_components, fingerprint_components)
    
    # 4. 获取融合摘要
    summary = fusion_engine.get_fusion_summary()
    
    # 5. 计算加权 CVE
    weighted = _calculate_weighted_cve(fused_components, vulnerabilities)
```

#### 3. 证据强度分级

| 等级 | 说明 | 权重 | 置信度 |
|------|------|------|--------|
| **Level A** | 双源匹配（SBOM + 指纹） | 1.25 | 高 |
| **Level B** | 仅 SBOM 声明 | 1.0 | 中 |
| **Level C** | 仅指纹识别 | 0.75 | 低 |

#### 4. 加权 CVE 统计

**返回字段**:
```json
"phase4_fusion": {
  "enabled": true,
  "sbom_id": "sbom_xxx",
  "evidence_summary": {
    "level_a": 5,
    "level_b": 3,
    "level_c": 2
  },
  "weighted_cve": {
    "critical_weighted": 6.25,
    "high_weighted": 4.0,
    "medium_weighted": 2.25,
    "low_weighted": 0.75,
    "total_weighted": 12.75
  }
}
```

**权重计算规则**:
- Critical (Level A): 1 × 1.25 = 1.25
- High (Level B): 1 × 1.0 = 1.0
- Medium (Level C): 1 × 0.75 = 0.75

---

## 🔧 技术变更

### 修改文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `api/main.py` | +15 行 | `/api/scan` 支持 `sbom_id` 参数 |
| `scanner/task_queue.py` | +150 行 | 融合引擎调用 + 加权计算 |
| `scripts/test_phase4_api.py` | +180 行 | 集成测试脚本（新增） |

### 新增文件

- `scripts/test_phase4_api.py` - Phase 4 集成测试脚本
- `V2.7.2_CUSTOMER_NOTIFICATION.md` - 客户通知邮件模板
- `V2.7.2_FINAL_SUMMARY.md` - 完成总结文档

---

## ✅ 测试验证

### 自动化测试

**测试脚本**: `scripts/test_phase4_api.py`

**测试用例**:
1. ✅ SBOM 导入和持久化
2. ✅ 融合引擎 A/B/C 分级
3. ✅ 任务队列 sbom_id 传递
4. ✅ 加权 CVE 计算

**测试结果**:
```
============================================================
✅ Phase 4 API 集成测试全部通过！
============================================================

[1/4] SBOM 导入测试：✅ 通过
[2/4] 融合引擎测试：✅ 通过 (A:1, B:1, C:1)
[3/4] 任务队列集成：✅ 通过 (sbom_id 传递正确)
[4/4] 加权 CVE 计算：✅ 通过 (权重准确)
```

### 手工验证

```bash
# 1. 语法检查
python3 -m py_compile api/main.py
python3 -m py_compile scanner/task_queue.py
# ✅ 通过

# 2. 模块导入
python3 -c "from scanner.task_queue import ScanQueue; from services.sbom.sbom_api import sbom_db"
# ✅ 通过

# 3. 集成测试
PYTHONPATH=/mnt/workspace/firmware_scanner python3 scripts/test_phase4_api.py
# ✅ 4/4 通过
```

---

## 📦 交付信息

### GitHub Release

- **Tag**: v2.7.2
- **URL**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.2
- **交付包**: firmware_scanner-2.7.2.zip（约 29MB）

### 交付包内容

```
firmware_scanner-2.7.2/
├── scanner/              # 核心扫描引擎（含融合调用）
├── api/                  # REST API（含 sbom_id 支持）
├── services/sbom/        # SBOM 服务（融合引擎 + API）
├── scripts/              # 脚本工具（含测试脚本）
├── tests/                # 单元测试
├── config.yaml           # 配置文件
├── requirements.txt      # Python 依赖
└── docs/                 # 文档
    ├── RELEASE_NOTES_v2.7.2.md
    ├── V2.7.2_CUSTOMER_NOTIFICATION.md
    └── V2.7.2_FINAL_SUMMARY.md
```

### 构建脚本

```bash
cd /mnt/workspace/firmware_scanner
./scripts/package_release_v2.7.2.sh
```

---

## 📋 升级指南

### 从 v2.7.0/v2.7.1 升级

1. **备份现有数据**
   ```bash
   cp -r /path/to/firmware_scanner /path/to/firmware_scanner.bak
   ```

2. **下载新交付包**
   ```bash
   wget https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/download/v2.7.2/firmware_scanner-2.7.2.zip
   ```

3. **解压并覆盖**
   ```bash
   unzip firmware_scanner-2.7.2.zip
   cd firmware_scanner-2.7.2
   ```

4. **重启服务**
   ```bash
   ./start.sh
   ```

### 从 v2.6.x 或更早版本升级

参考 `docs/DEPLOYMENT.md` 完整部署指南。

---

## 🔄 兼容性说明

### 向后兼容

- ✅ `/api/scan` 的 `sbom_id` 参数为**可选**，不影响现有调用
- ✅ 不传 `sbom_id` 时，行为与 v2.7.1 完全一致
- ✅ 所有现有 API 端点保持不变

### API 变更

| 端点 | 变更 | 兼容性 |
|------|------|--------|
| `POST /api/scan` | 新增 `sbom_id` 参数 | ✅ 向后兼容 |
| `POST /api/sbom/import` | 无变更 | ✅ 完全兼容 |
| `GET /api/sbom/{sbom_id}` | 无变更 | ✅ 完全兼容 |

---

## 📊 性能影响

### 融合分析开销

| 场景 | 额外耗时 | 说明 |
|------|---------|------|
| 无 SBOM | 0ms | 标准扫描流程 |
| 有 SBOM（小） | +50-100ms | <100 组件 |
| 有 SBOM（中） | +100-300ms | 100-500 组件 |
| 有 SBOM（大） | +300-500ms | >500 组件 |

### 内存占用

- 基础扫描：~200MB
- 融合分析：+50-100MB（取决于组件数）

---

## 🐛 已知问题

| 问题 | 影响 | 临时方案 | 计划修复 |
|------|------|---------|---------|
| Grype DB 缺失时降级 | CVE 匹配不可用 | 手动下载 DB | v2.8.0 自动下载 |
| 批量任务 completed_at 记录 | 时间戳可能为空 | 不影响功能 | v2.7.3 修复 |
| SMTP Mock 测试 | 需手动验证 | 使用真实 SMTP | v2.8.0 完善 |

---

## 📧 验收信息

- **验收编号**: VAL-FWSCAN-2026-015
- **验收状态**: ⏳ 待客户复测
- **复测重点**: Phase 4 SBOM 融合功能
- **文档位置**: `V2.7.2_FINAL_SUMMARY.md`

---

## 🔗 相关资源

- **GitHub Release**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.2
- **客户通知模板**: `V2.7.2_CUSTOMER_NOTIFICATION.md`
- **完成总结**: `V2.7.2_FINAL_SUMMARY.md`
- **测试脚本**: `scripts/test_phase4_api.py`
- **Phase 4 规划**: `V2.7.2_EMERGENCY_FIX.md`

---

## 👥 维护者信息

**攻城狮阿信 [Jackson]**  
邮箱：zhu80k@163.com  
日期：2026-09-03

---

⟦ v2.7.2 Release Notes 创建完成｜状态：文档已创建，待提交到 Git｜下一步：提交并推送｜锚点：RELEASE_NOTES_v2.7.2.md, v2.7.2 ⟧
