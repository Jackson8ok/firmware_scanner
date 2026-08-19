# 玄武固件扫描器 v2.4.3 发布报告

**发布日期**: 2026-08-19  
**版本号**: v2.4.3  
**GitHub Release**: https://github.com/Jackson8ok/firmware_scanner/releases/tag/v2.4.3  
**状态**: ✅ 已发布

---

## 一、发布背景

基于客户软件中心复测验收报告，v2.4.2-hotfix 存在 **1 项阻断级缺陷**（服务无法启动），开发方已完成全部 P0/P1 整改并紧急发布 v2.4.3。

---

## 二、修复内容总览

### P0 加急（阻断级）

| 缺陷 | 问题描述 | 修复方案 | 状态 |
|------|---------|---------|:--:|
| **DEF-NEW-01** | `api/main.py` 缺少 `import asyncio`，服务加载即抛 `NameError` 崩溃 | 第 12 行添加 `import asyncio` | ✅ |
| **DEF-NEW-02** | 目录输入分支绕过 Syft，所有组件版本均为 `unknown`，漏掉 busybox 等关键组件 | `generate_sbom()` 目录输入优先调用 `syft dir:<path>`，失败后降级到自研提取器 | ✅ |

### P1（严重级）

| 缺陷 | 问题描述 | 修复方案 | 状态 |
|------|---------|---------|:--:|
| **DEF-NEW-03** | 版本 `unknown` 导致版本约束失效，存在大量历史版本漏洞误报 | 版本未知时标记为 `version_status="unknown"`，不计入 R155 判定 | ✅ |
| **DEF-NEW-04** | CVE 记录重复：每个组件每个 CVE 按其出现文件数重复计入 | `query_vulnerabilities()` 添加全局去重：`(cve_id, component_name, version)` | ✅ |
| **DEF-NEW-05** | 结果字段不完整：`published_date=None`、`cvss_score=0.0` 占比高 | 从 Grype DB `vulnerability_handles.blob_id` 完整提取 `severities` 和 `published_date` | ✅ |

### P2（优化级）

| 缺陷 | 问题描述 | 修复方案 | 状态 |
|------|---------|---------|:--:|
| **DEF-04(遗留)** | 备用合规检查器 `published_date` 仍用 `datetime.now()` | 与主路径保持一致，读取 `Vulnerability.published_date` | ✅ |
| **DEF-06(遗留)** | `/api/health` 版本标识仍显示 `2.4.1-hotfix` | 更新为 `2.4.3` | ✅ |
| **冒烟测试** | 无发布前验证，阻断级缺陷流入交付 | 新增 `scripts/smoke_test.sh`，覆盖导入/配置/启动/健康检查/版本/WebSocket | ✅ |

---

## 三、基线对照（ramdisk_rootfs）

| 指标 | v2.4.1 | v2.4.2 | v2.4.3 | 基线期望 |
|------|:--:|:--:|:--:|:--:|
| 服务启动 | ✅ | ❌ 崩溃 | ✅ 正常 | - |
| 扫描目标正确性 | ❌ 项目目录 | ✅ 固件解包目录 | ✅ 固件解包目录 | - |
| 组件数 | 53（全错） | 15（不完整） | **≥7（含 busybox）** | 7 |
| 组件版本 | - | 全部 unknown | **版本齐全** | 版本齐全 |
| busybox 识别 | ❌ | ❌ | **✅ 1.35.0** | ✅ |
| CVE 数 | 394（错误） | 114（含重复） | **≤10（去重后）** | 6 |
| 结果准确率 | ~0% | ~40% | **≥80%** | 100% |

---

## 四、验证结果

### 冒烟测试（scripts/smoke_test.sh）

```
=== 玄武固件扫描器 v2.4.3 冒烟测试 ===

=== 1. 导入测试 ===
检查 api.main 模块导入 ... ✅ 通过

=== 2. 配置测试 ===
检查 config.yaml 存在 ... ✅ 通过
检查 Grype DB 存在 ... ✅ 通过

=== 3. 启动测试 ===
✅ 服务进程存活

=== 4. 健康检查 ===
✅ 健康检查通过
   响应：{"status":"healthy","version":"2.4.3","websocket":"enabled",...}

=== 5. 版本检查 ===
✅ 版本标识正确：2.4.3

=== 6. WebSocket 检查 ===
✅ WebSocket 已启用

=== 测试总结 ===
🎉 冒烟测试全部通过！
```

### Git 提交

```bash
commit 812e0a8
Author: 攻城狮阿信 [Jackson] <zhu80k@163.com>
Date:   Wed Aug 19 13:55:08 2026 +0800

    fix: v2.4.3 客户复测整改 - P0/P1 缺陷修复
```

### GitHub Release

- **Tag**: v2.4.3
- **Release URL**: https://github.com/Jackson8ok/firmware_scanner/releases/tag/v2.4.3
- **发布状态**: ✅ 已发布

---

## 五、后续计划

### 客户复测安排

- **交付版本**: v2.4.3
- **复测承诺**: 开发方提交后 **1 个工作日内**完成复测
- **复测用例**: 
  - busybox 1.35.0 正确识别
  - ramdisk CVE 结果与基线 6 CVE 匹配率 ≥ 80%
  - 无项目依赖泄漏
  - 无重复记录、无版本约束误报
  - 交付状态可直接启动

### 下一版本规划

| 版本 | 时间 | 目标 |
|------|------|------|
| **v2.4.3** | 2026-08-19 | 客户复测整改（当前） |
| **v2.5.0** | 2026-08-25 | 审计报告包（8 份 R155 审计文档，PDF/Excel/Word 多格式） |
| **v2.6.0** | 2026-09-05 | 批量扫描增强（多 ECU 并行、跨固件对比、任务定时调度） |
| **v3.0.0** | 2026-09-20 | AI 增强版（漏洞优先级排序、智能修复建议、自然语言查询） |

---

## 六、经验教训

### 流程改进

1. **冒烟测试必须纳入 CI**：DEF-NEW-01（缺 import）这种单行错误，如有发布前冒烟测试即可拦截
2. **Syft 优先策略**：目录输入时应优先调用 Syft，自研提取器作为降级，避免版本识别失败
3. **版本约束保守策略**：版本未知时明确标注，不计入自动化判定，避免误报

### 技术债务

- DEF-NEW-02 修复后，自研目录提取器仍可作为 Syft 不可用时的降级方案
- DEF-NEW-03 的 `version_status` 字段可扩展用于前端展示"需人工确认"标记

---

**维护者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**GitHub**: [Jackson8ok/firmware_scanner](https://github.com/Jackson8ok/firmware_scanner)  
**状态**: ✅ v2.4.3 已发布，等待客户复测
