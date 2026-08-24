# 玄武固件扫描器 v2.5.3 交付说明

## 📦 交付包内容

**交付包**: `firmware_scanner-2.5.3.zip`  
**大小**: ~15MB（不含 Grype DB）  
**日期**: 2026-08-24

### 包含目录

| 目录 | 文件数 | 说明 |
|------|--------|------|
| scanner/ | 18 | 扫描引擎核心代码 |
| api/ | 5 | FastAPI 接口层 |
| scripts/ | 18 | 部署/启动/测试脚本 |
| tests/ | 7 | 单元测试用例 |
| tools/ | 6 | grype 二进制和配置 |
| report_generator/ | 2 | 报告生成模块 |
| services/ | 2 | Node 报告服务 |
| db/grype/6/ | 1 | Grype 漏洞数据库（单独下载） |
| 文档 | 5 | README/DEPLOYMENT/USER_GUIDE/RELEASE_NOTES |

---

## 🔧 部署步骤

### 方式一：在线部署（推荐）

```bash
# 1. 解压
cd /mnt/workspace
unzip firmware_scanner-2.5.3.zip

# 2. 下载 Grype DB（约 1.9GB，需 5-10 分钟）
cd firmware_scanner
bash scripts/download_grype_db.sh

# 3. 启动服务
bash scripts/startup.sh

# 4. 验证
curl http://localhost:8000/api/health
```

### 方式二：离线部署

如目标机器无网络，需提前下载以下文件：

1. **Grype DB**: https://toolbox-data.anchore.io/grype/databases/vulnerability-db_v6_2024-08-20T08:17:02Z_1724141822.tar.gz (1.9GB)
2. **放置路径**: `/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db`

---

## ✅ 冒烟测试

```bash
# 1. 代码导入测试
python3 -c "import api.main" && echo "✅ 代码导入成功"

# 2. 服务启动测试
bash scripts/startup.sh
sleep 10
curl http://localhost:8000/api/health

# 应返回：{"status":"healthy","version":"2.5.3",...}
```

---

## 📋 v2.5.3 修复内容

### published_date 日期切割修复（1 行代码）

**复测结论**: VAL-FWSCAN-2026-006

```python
# 修复代码（仅 1 行）
if "+" in date_str:
    date_str = date_str.split("+")[0]
# 输入：'2023-08-22 19:16:31.08+00:00'
# 输出：'2023-08-22 19:16:31.08'
```

### 全部字段补全状态

| 字段 | v2.5.0 | v2.5.1 | v2.5.2 | v2.5.3 |
|------|--------|--------|--------|--------|
| cvss_score | 0% | 100% | 100% | 100% |
| epss_score | 0% | 100% | 100% | 100% |
| published_date | 0% | 0% | 0% | **≥90%** ✅ |

---

## 📞 联系方式

**维护者**: 攻城狮阿信 [Jackson]  
**邮箱**: zhu80k@163.com  
**GitHub**: https://github.com/Jackson8ok/firmware_scanner/releases/tag/v2.5.3

---

**复测安排**: 提交后 1 个工作日内完成（VAL-FWSCAN-2026-007）
