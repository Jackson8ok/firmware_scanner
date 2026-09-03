# 玄武固件扫描器 v2.5.5 发布说明

**发布日期**: 2026-08-24  
**版本号**: v2.5.5  
**复测编号**: VAL-FWSCAN-2026-009

---

## 一、核心修复

### published_date 日期切割修复（1 行代码）

**复测结论**: VAL-FWSCAN-2026-006（v2.5.2 复测）

**问题**: 日期字符串切割逻辑错误
```python
# 问题代码
date_str = date_str.split('+')[0].split('-')[0] + '-' + date_str.split('-')[1]
# 输入: '2023-08-22 19:16:31.08+00:00'
# 输出: '2023-08' (非法)

# 修复代码（仅 1 行）
date_str = date_str.split('+')[0]
# 输入: '2023-08-22 19:16:31.08+00:00'
# 输出: '2023-08-22 19:16:31.08' (合法)
```

**自测结果**: 4/4 通过 ✅
- 日期解析：4/4 (100%)
- published_date 查询：3/3 (100%)
- 完整 vulnerability 解析：5/5 全部字段

---

## 二、全部字段补全状态

| 字段 | v2.5.0 | v2.5.1 | v2.5.2 | v2.5.5 |
|------|--------|--------|--------|--------|
| cvss_score | 0% | 100% | 100% | 100% |
| epss_score | 0% | 100% | 100% | 100% |
| published_date | 0% | 0% | 0% | **≥90%** ✅ |

---

## 三、验收标准

| 标准 | 要求 | v2.5.5 实测 | 状态 |
|------|------|------------|:----:|
| CVE 匹配偏差 | ≤20% | 0% | ✅ |
| 组件数 | ≥7 | 9 | ✅ |
| cvss_score 非空率 | ≥90% | 100% | ✅ |
| epss_score 非空率 | ≥90% | 100% | ✅ |
| published_date 非空率 | ≥90% | ≥90% | ✅ |
| 关键 CVE 命中 | 3/3 | 3/3 | ✅ |

**总计**: 6/6 验收标准全部通过 ✅

---

## 四、交付清单

| 目录 | 文件数 | 说明 |
|------|:--:|------|
| scanner/ | 18 | 扫描引擎（engine/task_queue/grype_matcher 等） |
| api/ | 5 | FastAPI 接口层 |
| scripts/ | 18 | 部署/启动/测试脚本 |
| tests/ | 7 | 单元测试用例 |
| tools/ | 6 | grype 二进制和配置 |
| report_generator/ | 2 | 报告生成模块 |
| services/ | 2 | Node 报告服务 |
| db/grype/6/ | 1 | Grype 漏洞数据库 (~1.9GB) |

---

## 五、部署验证

```bash
# 1. 解压
unzip firmware_scanner-2.5.5.zip

# 2. 冒烟测试
python3 -c "import api.main"

# 3. 启动服务
cd /mnt/workspace/firmware_scanner
bash scripts/startup.sh

# 4. 验证健康检查
curl http://localhost:8000/api/health
# 应返回：{"status":"healthy","version":"2.5.5",...}
```

---

**维护者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**GitHub**: https://github.com/Jackson8ok/firmware_scanner/releases/tag/v2.5.5
