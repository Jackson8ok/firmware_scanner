# 玄武·AFVS v2.7.0 发布说明

**发布日期**: 2026-09-03  
**版本号**: v2.7.0  
**版本定位**: 组件指纹识别增强版  
**复测编号**: VAL-AFVS-2026-013

---

## 一、版本亮点

v2.7.0 针对 R155 成分审计场景中暴露的组件识别盲区进行系统性增强，解决 4 大类问题：

1. **大小写敏感漏检** → Phase 1 修复
2. **SBOM 与实物不一致静默** → Phase 2 修复
3. **版本未知组件报告不清晰** → Phase 3 修复
4. **符号裁剪组件漏检** → Phase 4 修复（架构升级）

**总计工作量**: 15 天（4 Phase，全部完成）

---

## 二、核心功能矩阵

| Phase | 功能 | 状态 | 说明 |
|-------|------|:--:|------|
| **Phase 1** | 大小写不敏感修复 | ✅ | 10 个核心组件支持大小写不敏感匹配 |
| **Phase 2** | SBOM × 指纹一致性校验 | ✅ | SPDX/CycloneDX 解析 + 比对报告 + 告警 |
| **Phase 3** | 版本未知组件优化 | ✅ | 置信度分级 + CVE 策略优化 + R155 判定优化 |
| **Phase 4** | SBOM 融合架构 | ✅ | A/B/C 类证据分级 + CVE 加权统计 |

---

## 三、新增 API 端点

### SBOM 相关（Phase 2）
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/sbom/import` | POST | 导入 SBOM 文件（SPDX/CycloneDX/CSV） |
| `/api/sbom/{id}` | GET | 获取 SBOM 详情 |
| `/api/sbom/{id}/comparison` | GET | SBOM × 指纹比对报告 |
| `/api/sbom/{id}` | DELETE | 删除 SBOM |

### SBOM 融合（Phase 4）
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/scan` (带 sbom_id) | POST | 融合扫描（SBOM + 指纹） |

---

## 四、证据强度分级

| 级别 | 含义 | CVE 权重 | 示例 |
|------|------|---------|------|
| **A** | 指纹确认版本 | 100% | BusyBox v1.35.0 (SBOM + 指纹一致) |
| **B** | SBOM 声明 | 50% | wolfSSL 5.8.4 (仅 SBOM，可能符号裁剪) |
| **C** | 仅指纹或版本未知 | 25% | FreeRTOS (版本未知) |

---

## 五、CVE 加权统计

**示例**:
```
原始 CVE: 67 个 (Critical=11, High=20, Medium=25, Low=11)
加权 CVE: 42.5 个 (Critical=7.25, High=12.5, Medium=15.5, Low=7.25)
```

**权重计算**:
- A 类组件的 CVE: × 1.0
- B 类组件的 CVE: × 0.5
- C 类组件的 CVE: × 0.25

---

## 六、交付清单

| 目录 | 文件数 | 说明 |
|------|:--:|------|
| scanner/ | 18 | 扫描引擎（engine.py 含 Phase 1-4 全部增强） |
| api/ | 6 | FastAPI 接口层（含 SBOM API） |
| services/sbom/ | 3 | SBOM 解析器 + 融合引擎 + API |
| scripts/ | 18 | 部署/启动/测试脚本 |
| tests/ | 7 | 单元测试用例 |
| tools/ | 6 | grype 二进制和配置 |
| report_generator/ | 2 | 报告生成模块 |

**注意**: 本交付包**不含 Grype DB**（需单独下载或在线更新）

---

## 七、部署验证

```bash
# 1. 解压
unzip firmware_scanner-2.7.0.zip

# 2. 冒烟测试
python3 -c "from services.sbom.sbom_fusion import SBOMFusionEngine; print('✅ v2.7.0 加载成功')"

# 3. 启动服务
cd /mnt/workspace/firmware_scanner
bash scripts/startup.sh

# 4. 验证健康检查
curl http://localhost:8765/api/health
# 应返回：{"status":"healthy","version":"2.7.0",...}

# 5. 测试 SBOM 导入
curl -X POST http://localhost:8765/api/sbom/import \
  -F "file=@test_sbom.spdx.json" \
  -F "firmware_id=test_001"
```

---

## 八、验收标准

| 标准 | 要求 | v2.7.0 实测 | 状态 |
|------|------|------------|:----:|
| Phase 1 大小写不敏感 | 12/12 测试通过 | 100% | ✅ |
| Phase 2 SBOM 解析 | SPDX/CycloneDX/CSV | 3/3 格式 | ✅ |
| Phase 2 比对引擎 | 三类差异识别 | 100% | ✅ |
| Phase 3 置信度分级 | high/medium/low | 3 级 | ✅ |
| Phase 4 融合引擎 | A/B/C 类分级 | 100% | ✅ |
| Phase 4 CVE 加权 | 加权统计正确 | 100% | ✅ |
| 向后兼容 | 无 SBOM 时行为一致 | 验证通过 | ✅ |

**总计**: 7/7 验收标准全部通过 ✅

---

## 九、技术文档

| 文档 | 说明 |
|------|------|
| `REQUIREMENTS_v2.7.0_2026-08-28.md` | 需求规划 |
| `PHASE1_COMPLETE_REPORT_2026-08-28.md` | Phase 1 完成报告 |
| `PHASE2_COMPLETE_REPORT_2026-09-01.md` | Phase 2 完成报告 |
| `PHASE3_COMPLETE_REPORT_2026-09-02.md` | Phase 3 完成报告 |
| `PHASE4_COMPLETE_REPORT_2026-09-03.md` | Phase 4 完成报告 |

---

## 十、已知问题（v2.7.1 修复）

| 问题 | 级别 | 计划 |
|------|------|------|
| 批量任务 completed_at 未记录 | P2 | v2.7.1 |
| 批量路由格式不统一 | P2 | v2.7.1 |
| SMTP Mock 测试方案 | P2 | v2.7.1 |

---

**维护者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**GitHub**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.0

---

**生产就绪** ✅ | **认证场景推荐** ✅ | **v2.7.0 功能验收关闭** ✅
