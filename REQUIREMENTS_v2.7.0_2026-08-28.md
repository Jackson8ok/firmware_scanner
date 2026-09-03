# AFVS v2.7.0 需求规划

**创建日期**: 2026-08-28  
**优先级**: P0 - 组件识别增强  
**来源**: 实际固件验收测试 (ARM Cortex-M 车载控制器)  
**文档编号**: REQ-v2.7.0-2026-001  

---

## 📋 版本定位

**v2.7.0 - 组件指纹识别增强版**

针对 R155 成分审计场景中暴露的组件识别盲区进行系统性增强，重点解决：
- 大小写敏感导致的漏检
- SBOM 与二进制指纹不一致时的静默问题
- 符号裁剪组件的识别盲区
- 版本未知组件的报告优化

---

## 🎯 需求列表

### Phase 1: 组件模式库大小写不敏感修复【P0】

**问题编号**: ISSUE-FWSCAN-2026-001  
**严重度**: 🔴 高  
**来源**: 实际固件验收测试 (lwIP 漏检案例)

#### 问题描述
组件模式匹配使用大小写敏感正则，导致固件中大写标识（如 `LWIP`）未被识别。

**证据**:
```
# 固件字符串提取
######-%s::Coping data to LWIP stack ... START.
######-%s::Copy data to LWIP stack ... DONE!
transfer_lwip_to_spidev_copy_buff

# 当前匹配模式（大小写敏感）
'lwIP': (re.compile(r'lwIP|tcp_connect|udp_sendto|netif_add|pbuf_alloc'), 'network')
# → 0 命中（漏检）
```

#### 修复方案
更新 `scanner/engine.py` 组件模式库，关键标识使用大小写不敏感匹配：

```python
# 修改前
'lwIP':     (re.compile(r'lwIP|tcp_connect|udp_sendto|netif_add|pbuf_alloc'), 'network'),
'wolfSSL':  (re.compile(r'wolfSSL_|WOLFSSL_|SSL_set_fd|wolfSSL_Init'), 'crypto'),
'mbedTLS':  (re.compile(r'mbedtls_|MBEDTLS_|mbedtls_ssl_init'), 'crypto'),
'OpenSSL':  (re.compile(r'OPENSSL_|SSL_library_init|EVP_'), 'crypto'),
'FreeRTOS': (re.compile(r'FreeRTOS|xTaskCreate|pvPortMalloc|xSemaphoreCreate'), 'rtos'),

# 修改后（添加 (?i) 标志）
'lwIP':     (re.compile(r'(?i)lwip|netif_add|pbuf_alloc|tcp_connect|udp_sendto'), 'network'),
'wolfSSL':  (re.compile(r'(?i)wolfssl|wolfcrypt|ssl_set_fd'), 'crypto'),
'mbedTLS':  (re.compile(r'(?i)mbedtls'), 'crypto'),
'OpenSSL':  (re.compile(r'(?i)openssl|ssl_library_init|evp_'), 'crypto'),
'FreeRTOS': (re.compile(r'(?i)freertos|xtaskcreate|pvportmalloc|xsemaphorecreate'), 'rtos'),
```

#### 验收标准
- [ ] 同一固件由「识别 1 组件（仅 FreeRTOS）」变为「识别 2 组件（FreeRTOS + lwIP）」
- [ ] 无误报（不引入额外组件匹配）
- [ ] 回归测试：v2.5.4 终验固件样本匹配结果一致

#### 工作量估算
- 开发：0.5 天
- 测试：0.5 天
- **总计**: 1 天

---

### Phase 2: SBOM × 指纹一致性校验【P0】

**问题编号**: ISSUE-FWSCAN-2026-002  
**严重度**: 🔴 高  
**来源**: 实际固件验收测试 (wolfSSL 5.8.4 案例)

#### 问题描述
研发提供的 SBOM 声明固件包含 **wolfSSL 5.8.4**，但二进制指纹扫描未找到任何 wolfSSL 特征（0 命中）。当前工具对此完全静默，导致：
- 若二进制实际链接了 wolfSSL 但符号被裁剪 → 漏报 67 个 CVE（含 11 个 Critical）
- 若二进制确未包含 → SBOM 与实物不符，属于成分清单质量问题

#### 功能需求

**2.1 SBOM 导入接口**
```python
POST /api/sbom/import
Request:
  - file: SBOM 文件 (SPDX/CycloneDX JSON/CSV)
  - firmware_id: 关联的固件 ID

Response:
  {
    "sbom_id": "sbom_xxx",
    "components_count": 15,
    "status": "parsed"
  }
```

**2.2 SBOM × 指纹比对报告**
```python
GET /api/sbom/{sbom_id}/comparison

Response:
  {
    "matched": [
      {"name": "FreeRTOS", "sbom_version": "10.4.3", "fingerprint_version": "10.4.3", "status": "confirmed"}
    ],
    "sbom_only": [
      {"name": "wolfSSL", "version": "5.8.4", "warning": "二进制未命中，可能符号裁剪或未链接"}
    ],
    "fingerprint_only": [
      {"name": "busybox", "version": "1.35.0", "warning": "SBOM 未声明，可能遗漏"}
    ]
  }
```

**2.3 不一致告警**
- SBOM 有但二进制未命中 → ⚠️ 黄色告警「可能符号裁剪」
- 二进制命中但 SBOM 未声明 → ⚠️ 黄色告警「SBOM 可能遗漏」
- 两者版本不一致 → ⚠️ 黄色告警「版本不一致」

#### 验收标准
- [ ] 支持 SPDX 2.3 / CycloneDX 1.4 格式导入
- [ ] 比对报告正确显示三类差异（matched / sbom_only / fingerprint_only）
- [ ] 不一致告警在 UI 和 API 响应中可见
- [ ] wolfSSL 案例复现：SBOM 声明 5.8.4，二进制 0 命中 → 正确告警

#### 工作量估算
- 开发：3 天
- 测试：1 天
- **总计**: 4 天

---

### Phase 3: 版本未知组件优化标注【P1】

**问题编号**: ISSUE-FWSCAN-2026-003  
**严重度**: 🟡 中  
**来源**: 实际固件验收测试 (FreeRTOS 版本 unknown 案例)

#### 问题描述
FreeRTOS 可被识别（命中 `FreeRTOS Kernel Fault` 等），但版本始终为 `unknown`——内核版本通常不以字符串形式固化在固件中。

#### 功能需求

**3.1 报告标注优化**
```json
{
  "name": "FreeRTOS",
  "version": "unknown",
  "version_note": "版本未知（需厂商提供）",
  "confidence": "high",
  "evidence": ["FreeRTOS Kernel Fault", "malloc failed hook"]
}
```

**3.2 CVE 匹配策略**
- 版本已知 → 精确匹配 CVE
- 版本未知 → 匹配该组件全部 CVE，但标注「版本未知，可能包含以下漏洞（需厂商确认版本）」

**3.3 可选：版本推断增强**
- 针对 FreeRTOS 增加版本号字符串特征（如 `tTaskCreate`/`vTaskDelay` 附近的版本宏）
- 支持从厂商版本说明/构建元数据注入版本

#### 验收标准
- [ ] 版本未知组件在报告中标注「需厂商提供」
- [ ] CVE 列表正确显示并标注不确定性
- [ ] UI 中版本未知组件有特殊视觉标识（如 ⚠️ 图标）

#### 工作量估算
- 开发：1.5 天
- 测试：0.5 天
- **总计**: 2 天

---

### Phase 4: SBOM 融合架构升级【P0】

**问题编号**: ISSUE-FWSCAN-2026-004  
**严重度**: 🔴 高 (架构)  
**来源**: 实际固件验收测试 (符号裁剪组件漏检)

#### 问题描述
静态链接且已 strip 的组件（如 wolfSSL），二进制中无函数名/版本字符串，纯字符串指纹法无法识别。本案二进制指纹扫描报 0 CVE，但一旦以研发 SBOM 为准，该组件带入 67 个 CVE。

#### 架构升级方案

**4.1 双源输入架构**
```
┌─────────────────────────────────────┐
│         扫描任务输入                 │
├─────────────────────────────────────┤
│  1. 固件文件（二进制指纹源）         │
│  2. SBOM 文件（成分声明源，可选）    │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│       组件识别引擎（增强版）         │
├─────────────────────────────────────┤
│  - 二进制指纹识别（现有）            │
│  - SBOM 解析（新增）                 │
│  - 融合决策逻辑（新增）              │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│         融合决策逻辑                 │
├─────────────────────────────────────┤
│  IF 指纹确认版本                     │
│    THEN 以指纹为准（证据强度高）     │
│  ELSE IF SBOM 声明                   │
│    THEN 按 SBOM 版本匹配             │
│         标注「来源：SBOM（未经确认）」│
│  ELSE                                │
│    THEN 版本 unknown                 │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│         报告输出（分层）             │
├─────────────────────────────────────┤
│  A 类：指纹确认组件（高置信度）      │
│  B 类：SBOM 声明组件（中置信度）     │
│  C 类：版本未知组件（低置信度）      │
└─────────────────────────────────────┘
```

**4.2 证据强度分级**
| 级别 | 来源 | 置信度 | 报告标识 |
|------|------|--------|----------|
| A | 二进制指纹确认版本 | 高 | ✅ |
| B | SBOM 声明（指纹未命中） | 中 | ⚠️ |
| C | 指纹识别但版本未知 | 低 | ❓ |

**4.3 API 变更**
```python
POST /api/scan
Request:
  {
    "firmware_file": "...",
    "sbom_file": "..."  # 可选
  }

Response:
  {
    "components": {
      "confirmed": [...],    # A 类
      "sbom_declared": [...], # B 类
      "version_unknown": [...] # C 类
    },
    "warnings": [...]
  }
```

#### 验收标准
- [ ] SBOM 导入后，裁剪组件（wolfSSL）正确识别并标注「来源：SBOM」
- [ ] 报告分层显示 A/B/C 三类组件
- [ ] CVE 统计按证据强度加权（A 类 100%, B 类 50%, C 类 25%）
- [ ] 向后兼容：无 SBOM 时行为与 v2.6.0 一致

#### 工作量估算
- 架构设计：1 天
- 开发：5 天
- 测试：2 天
- **总计**: 8 天

---

## 📊 版本规划汇总

| Phase | 需求 | 优先级 | 工作量 | 依赖 |
|-------|------|:--:|:--:|------|
| Phase 1 | 大小写不敏感修复 | P0 | 1 天 | 无 |
| Phase 2 | SBOM × 指纹一致性校验 | P0 | 4 天 | Phase 1 |
| Phase 3 | 版本未知组件优化 | P1 | 2 天 | 无 |
| Phase 4 | SBOM 融合架构升级 | P0 | 8 天 | Phase 2 |
| **总计** | - | - | **15 天** | - |

---

## 🎯 里程碑计划

| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| Phase 1 完成 | 2026-09-01 | 组件模式库更新，lwIP 漏检修复 |
| Phase 2 完成 | 2026-09-05 | SBOM 导入 + 比对报告 + 告警 |
| Phase 3 完成 | 2026-09-08 | 版本未知组件优化标注 |
| Phase 4 完成 | 2026-09-18 | SBOM 融合架构上线 |
| v2.7.0 发布 | 2026-09-20 | GitHub Release + 交付包 |

---

## 🧪 测试计划

### 回归测试（核心能力）
- [ ] CVE 匹配偏差 ≤20% (v2.5.4 终验样本)
- [ ] 组件数 ≥7 (busybox 1.35.0 样本)
- [ ] cvss/epss/date 非空率 ≥90%
- [ ] 关键 CVE 3/3 命中
- [ ] 无泄漏/无重复

### 新功能测试
- [ ] lwIP 大小写不敏感匹配（问题 1 样本）
- [ ] SBOM × 指纹比对报告（wolfSSL 案例）
- [ ] FreeRTOS 版本未知标注
- [ ] SBOM 融合架构（A/B/C 类组件分层）

---

## 📝 技术债务

| 债务 | 来源 | 建议偿还时间 |
|------|------|-------------|
| 批量任务 completed_at 未记录 | v2.6.0 观察项 | v2.7.0 或 v2.8.0 |
| 批量路由格式不统一 | v2.6.0 观察项 | v2.7.0 |
| SMTP Mock 测试方案 | v2.6.0 观察项 | v2.7.0 |

---

## 🔗 关联文档

| 文档 | 链接 |
|------|------|
| 组件指纹识别改进建议 | `/mnt/workspace/复测结论.md` |
| v2.6.0 复测报告 (VAL-FWSCAN-2026-012) | 同上 |
| v2.6.0 Release Notes | https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.6.0 |

---

**攻城狮阿信 [Jackson]**  
**zhu80k@163.com**  
**2026-08-28 19:00**
