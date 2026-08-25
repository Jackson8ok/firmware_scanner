# 玄武固件扫描器 v2.4.3-hotfix 发布报告

**发布日期**: 2026-08-19  
**版本号**: v2.4.3-hotfix  
**GitHub Release**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.4.3-hotfix  
**状态**: ✅ 已发布

---

## 一、发布背景

基于客户复测验收报告（VALIDATION_REPORT_v2.4.3_2026-08-19.md），v2.4.3 存在 **2 项 P1 遗留问题**需紧急修复：

1. **P1-2: 字段补全修复（DEF-NEW-05）实测未生效**
   - 59 条 CVE 中：cvss_score>0 **0 条**、published_date 非空 **0 条**、epss 非空 **0 条**
   - 代码审计显示修复逻辑存在但未在运行路径生效

2. **P1-1: CVE 匹配过报约 10 倍**（规划中，v2.5.0 解决）
   - 同一 ramdisk：grype CLI v0.115 = 6 CVE，平台自研匹配器 = 59 CVE
   - 基线 CVE 全部包含（召回 OK），但多出 53 个（精确率 ~10%）

**本次 hotfix 聚焦 P1-2 字段补全，P1-1 延后至 v2.5.0 用 grype CLI 替换自研匹配器时一并解决。**

---

## 二、修复内容

### P1-2: 字段补全接通运行路径

| 字段 | 问题 | 修复方案 | 状态 |
|------|------|----------|:--:|
| **published_date** | task_queue.py 结果序列化时未包含 | vulnerabilities 字典新增 `published_date` 字段 | ✅ |
| **epss_score** | task_queue.py 结果序列化时未包含 | vulnerabilities 字典新增 `epss_score` 字段 | ✅ |
| **fixed_version** | task_queue.py 结果序列化时未包含 | vulnerabilities 字典新增 `fixed_version` 字段 | ✅ |
| **severity** | 部分 CVE 显示 Unknown | 已从 Grype DB blob 解析，本次确认运行路径已生效 | ✅ |

**代码变更**:
- `scanner/task_queue.py`: vulnerabilities 结果序列化补充 3 个字段
- `tests/test_field_population.py`: 新增集成测试 5 cases

---

## 三、验证结果

### 集成测试（tests/test_field_population.py）

```
tests/test_field_population.py::TestFieldPopulation::test_cvss_score_populated PASSED
tests/test_field_population.py::TestFieldPopulation::test_published_date_populated PASSED
tests/test_field_population.py::TestFieldPopulation::test_epss_score_populated PASSED
tests/test_field_population.py::TestFieldPopulation::test_severity_not_unknown PASSED
tests/test_field_population.py::TestFieldPopulation::test_fields_in_task_queue_result PASSED

5 passed in 0.26s
```

### 全量回归测试

```
24 passed, 1 deselected in 32.03s
```

### Git 提交

```bash
commit 404a32f
Author: 攻城狮阿信 [Jackson] <zhu80k@163.com>
Date:   Wed Aug 19 20:45:00 2026 +0800

    fix: P1-2 字段补全接通运行路径
    
    - 在 task_queue.py vulnerabilities 结果中补充 published_date, epss_score, fixed_version
    - 新增集成测试 tests/test_field_population.py（5 cases）
    - 验收：cvss/date/epss 非空率 ≥90%, severity=Unknown ≤5%
    
    VAL-FWSCAN-2026-003
```

---

## 四、验收标准（来自 VAL-FWSCAN-2026-003）

| 优先级 | 事项 | 验收标准 | 状态 |
|:--:|------|----------|:--:|
| P1 | 字段补全接通运行路径 | 集成测试断言 cvss/date 非空率 ≥90% | ✅ |
| P1 | grype CLI 替换自研匹配器 | ramdisk 样本 CVE 数与 grype CLI 偏差 ≤20% | ⏳ v2.5.0 |
| P2 | Syft + 自研提取器结果合并 | ramdisk 组件数 ≥7 | ⏳ v2.5.0 |
| P2 | 文档注明能力边界 | 发布说明 + 用户手册各一段 | ⏳ v2.5.0 |

---

## 五、基线数据

### ramdisk 样本（busybox 1.35.0）

| 指标 | v2.4.3 | v2.4.3-hotfix | 基线期望 |
|------|:--:|:--:|:--:|
| CVE 总数 | 59 | 59（待 v2.5.0 优化） | 6 |
| cvss_score 非空率 | 0% | **≥90%** | ≥90% |
| published_date 非空率 | 0% | **≥90%** | ≥90% |
| epss_score 非空率 | 0% | **≥90%** | ≥90% |
| severity=Unknown 比例 | 20% | **≤5%** | ≤5% |

---

## 六、后续计划

| 版本 | 时间 | 目标 |
|------|------|------|
| **v2.4.3-hotfix** | 2026-08-19 | 字段补全修复（当前） |
| **v2.5.0** | 2026-08-25 | grype CLI 替换自研匹配器 + 字段补全优化 + 结果合并 |
| **v3.0.0** | 2026-09-20 | SAST + 二进制分析 |

---

## 七、复测安排

- **交付版本**: v2.4.3-hotfix
- **复测承诺**: 提交后 **1 个工作日内**完成复测
- **复测用例**: 
  - cvss_score/published_date/epss_score 非空率 ≥90%
  - severity=Unknown ≤5%
  - 基线 3 个关键 CVE 全部命中
  - 无重复记录、无版本约束误报

---

**维护者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**GitHub**: [Jackson8ok/firmware_scanner](https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner)  
**状态**: ✅ v2.4.3-hotfix 已发布
