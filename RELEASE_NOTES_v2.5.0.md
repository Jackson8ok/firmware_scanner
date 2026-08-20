# 玄武固件扫描器 v2.5.0 发布说明

**发布日期**: 2026-08-20  
**版本号**: v2.5.0  
**GitHub Release**: https://github.com/Jackson8ok/firmware_scanner/releases/tag/v2.5.0  
**状态**: ✅ 已发布

---

## 一、核心变更

### 1. grype CLI 集成（P1）

**变更**: 使用 grype CLI v0.117.0 作为 CVE 匹配引擎

**优势**:
- 使用 grype 官方匹配逻辑，精度有保证
- 支持 version ranges、CPE、distroless 等特性
- 结果与 grype CLI 基准一致

**实现**:
- 新增 `scanner/grype_matcher.py`（GrypeCLIMatcher 类）
- 修改 `scanner/task_queue.py`，集成 grype CLI 调用
- 新增 `tests/test_grype_integration.py`（7 passed）

**验证结果**:
- ✅ 目录模式返回 21 CVE（owrt_15.05.1.squashfs）
- ✅ 扫描耗时 ~36s
- ✅ 降级逻辑可用（grype CLI 失败时回退到自研匹配器）

### 2. Syft + 自研提取器结果合并（P2）

**变更**: 合并 Syft + 自研提取器结果，去重后返回

**策略**:
1. 优先 Syft（覆盖大部分场景）
2. 自研提取器作为补充（覆盖 Syft 遗漏的库文件）
3. 全局去重：(name, version)

**实现**:
- 新增 `SBOMGenerator.generate_sbom_merged()` 方法
- 修改 `generate_sbom()` 统一调用合并逻辑
- 新增 `tests/test_sbom_merge.py`（5 passed）

**验证结果**:
- ✅ Syft + 自研结果合并去重
- ✅ Syft 失败时降级到自研提取器
- ✅ 自研提取器失败时保留 Syft 结果
- ✅ ramdisk 组件数 100（自研提取器）

### 3. 文档能力边界（P2）

**新增文档**:
- `USER_GUIDE.md` - 用户指南，明确说明能力边界
- `DEPLOYMENT.md` - 部署指南，包含 grype CLI 安装配置
- `README.md` - 更新技术架构，反映 v2.5.0 变更

**能力边界说明**:
- ✅ 支持：二进制固件、文件系统镜像
- ⚠️ 有限支持：MCU 固件
- ❌ 不支持：源码树（建议交付标准 SBOM）

---

## 二、技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    v2.5.0 扫描流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Firmware → Extract → SBOM (Syft + 自研合并) → grype CLI   │
│                                                             │
│  可选分支：                                                  │
│  Source Tree → Recipe Parser → CycloneDX SBOM → grype CLI  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、测试结果

### 实际环境验证

**测试样本**: `uploads/owrt_15.05.1.squashfs` (6.9 MB)

| 指标 | 目标 | 实际结果 | 状态 |
|------|------|----------|:--:|
| 组件数 | ≥7 | 100 | ✅ 通过 |
| CVE 数 | >0 | 21 | ✅ 通过 |
| Critical | - | 3 | ✅ |
| High | - | 13 | ✅ |
| 扫描耗时 | <60s | ~55s | ✅ 通过 |

### 单元测试

```bash
$ python -m pytest tests/ -v -m "not slow"

tests/test_grype_integration.py::TestGrypeCLIIntegration::test_grype_cli_not_found PASSED
tests/test_grype_integration.py::TestGrypeCLIIntegration::test_scan_nonexistent_path PASSED
tests/test_grype_integration.py::TestGrypeCLIIntegration::test_parse_empty_grype_output PASSED
tests/test_grype_integration.py::TestGrypeCLIIntegration::test_parse_single_match PASSED
tests/test_grype_integration.py::TestGrypeCLIIntegration::test_deduplication PASSED
tests/test_grype_integration.py::TestGrypeCLIIntegration::test_scan_with_mock_grype PASSED
tests/test_grype_integration.py::TestGrypeCLIIntegration::test_fallback_to_legacy_matcher PASSED
tests/test_sbom_merge.py::TestMergedSBOM::test_merge_syft_and_custom PASSED
tests/test_sbom_merge.py::TestMergedSBOM::test_deduplication PASSED
tests/test_sbom_merge.py::TestMergedSBOM::test_syft_failure_fallback PASSED
tests/test_sbom_merge.py::TestMergedSBOM::test_custom_extractor_failure PASSED
tests/test_sbom_merge.py::TestMergedSBOM::test_both_extractors_empty PASSED

36 passed, 1 deselected in 31.24s
```

### Git 提交

```bash
commit f9cb65a
Author: 攻城狮阿信 [Jackson] <zhu80k@163.com>
Date:   Thu Aug 20 16:45:00 2026 +0800

    docs: v2.5.0 验证通过 - 21 CVE, 100 组件
    
    - 更新 VALIDATION_REPORT_v2.5.0_2026-08-20.md
    - 验证结果：组件数 100 ✅, CVE 21 ✅, 耗时 ~55s ✅
    - 修复：unsquashfs 安装、Grype DB 软链接、EPSS 超时、目录模式
```

---

## 四、验收标准

| 优先级 | 事项 | 验收标准 | 状态 |
|:--:|------|----------|:--:|
| P1 | grype CLI 替换自研匹配器 | 目录模式返回 CVE（21 CVE） | ✅ 通过 |
| P1 | 字段补全运行路径已生效 | 集成测试断言 cvss/date/epss 非空率 ≥90% | ✅ 已修复 |
| P2 | Syft + 自研提取器结果合并 | 组件数 ≥7（100） | ✅ 通过 |
| P2 | 文档注明能力边界 | 发布说明 + 用户手册各一段 | ✅ 已完成 |

---

## 五、后续计划

| 版本 | 时间 | 目标 |
|------|------|------|
| **v2.5.0** | 2026-08-20 | grype CLI 集成 + 结果合并 + 文档边界 ✅ |
| **v3.0.0** | 2026-09-20 | SAST + 二进制分析 |

### Phase 4（可选）：构建配方 SBOM 提取

**定位**: 源码形态交付物的快速预筛，不替代二进制扫描

**实现内容**:
- OpenWrt/Buildroot/Yocto Makefile 解析
- PKG_NAME/PKG_VERSION/DEPENDS 提取
- CycloneDX SBOM 生成

**决策点**: 客户明确需要源码扫描能力时启动

---

## 六、升级指南

### 从 v2.4.3 升级到 v2.5.0

```bash
# 1. 备份数据
cp -r /mnt/workspace/firmware_scanner/data /mnt/workspace/backup_v2.4.3

# 2. 拉取最新代码
cd /mnt/workspace/firmware_scanner
git pull origin main

# 3. 安装依赖
bash scripts/setup_grype.sh

# 4. 重启服务
./scripts/restart.sh

# 5. 验证
curl http://localhost:8000/api/health
```

---

**维护者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**GitHub**: [Jackson8ok/firmware_scanner](https://github.com/Jackson8ok/firmware_scanner)  
**状态**: ✅ v2.5.0 已发布
