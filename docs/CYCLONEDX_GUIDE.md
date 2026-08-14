# 📦 CycloneDX SBOM 使用指南

## 概述

Firmware Scanner 现在支持生成符合 **CycloneDX 1.4** 标准的软件物料清单（SBOM），这是一种轻量级、开源的 SBOM 标准，广泛应用于供应链安全。

### 为什么选择 CycloneDX？

- ✅ **行业标准**: OWASP Top 10 推荐，被 NVD 和各大安全平台采用
- ✅ **兼容性**: 支持与 Dependency-Track、Snyk、JFrog Xray 等工具集成
- ✅ **标准化**: 包含组件、漏洞、依赖关系等完整信息
- ✅ **互操作性**: JSON/XML双格式支持

---

## 安装依赖

```bash
# 安装 CycloneDX Python 库
pip install cyclonedx-python-lib

# 验证安装
python -c "from cyclonedx.model.bom import Bom; print('✅ OK')"
```

---

## 使用方法

### 1️⃣ API 端点

#### 下载 CycloneDX SBOM

```bash
# 基本用法
curl -X GET "http://localhost:8000/api/sbom/{task_id}?format=cyclonedx" \
  -o sbom.cyclonedx.json

# 指定 Schema 版本
curl -X GET "http://localhost:8000/api/sbom/{task_id}?format=cyclonedx&schema_version=1.3" \
  -o sbom-1.3.json

# 验证 SBOM
curl -X GET "http://localhost:8000/api/sbom/{task_id}/validate"
```

#### Python SDK

```python
import requests

# 执行扫描并获取任务 ID
response = requests.post(
    "http://localhost:8000/api/scan",
    data={'firmware_id': 'my_firmware', 'firmware_type': 'elf'}
)
task_id = response.json()['task_id']

# 等待完成...
# task_status = requests.get(f"http://localhost:8000/api/task/{task_id}")

# 下载 SBOM
sbom_response = requests.get(
    f"http://localhost:8000/api/sbom/{task_id}",
    params={'format': 'cyclonedx', 'schema_version': '1.4'}
)

with open('sbom.cyclonedx.json', 'wb') as f:
    f.write(sbom_response.content)
```

---

### 2️⃣ 命令行工具

```python
# 直接生成 SBOM
python test_cyclonedx.py

# 运行测试套件
python -m pytest tests/test_cyclonedx.py -v
```

---

## SBOM 格式示例

### CycloneDX 1.4 JSON 结构

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "serialNumber": "urn:uuid:3e671687-395b-41f5-a30f-a58921a69b79",
  "version": 1,
  "metadata": {
    "timestamp": "2026-08-04T10:00:00Z",
    "tools": [
      {
        "name": "Firmware Scanner",
        "version": "2.1-alpha"
      }
    ]
  },
  "components": [
    {
      "type": "library",
      "name": "FreeRTOS",
      "version": "10.4.6",
      "cpe": "cpe:2.3:o:freertos:freertos:10.4.6:*:*:*:*:*:*:*",
      "purl": "pkg:pypi/freertos@10.4.6"
    }
  ],
  "vulnerabilities": [
    {
      "id": "CVE-2022-30801",
      "source": {"name": "NVD"},
      "ratings": [
        {
          "score": 8.8,
          "severity": "high",
          "method": "CVSSv31"
        }
      ],
      "recommendations": "Upgrade to FreeRTOS 202202.00 or later",
      "affects": [
        {"ref": "FreeRTOS@10.4.6"}
      ]
    }
  ]
}
```

---

## 与外部工具集成

### 1. OWASP Dependency-Track

```bash
# 上传 SBOM 到 Dependency-Track
curl -X POST "https://dependency-track.example.com/api/v1/bom" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "project=my-firmware-project" \
  -F "bom=@sbom.cyclonedx.json"
```

### 2. Snyk

```bash
# 使用 Snyk CLI 导入 SBOM
snyk sbom analyze --file=sbom.cyclonedx.json
```

### 3. JFrog Xray

```bash
# 通过 Xray REST API 导入
curl -X POST "https://xray.jfrog.io/xar/api/v1/sbom/import" \
  -u "admin:password" \
  -H "Content-Type: application/json" \
  -d @sbom.cyclonedx.json
```

---

## 常见问题

### Q1: 安装 cyclonedx-python-lib 失败？

```bash
# 尝试升级 pip 后重新安装
python -m pip install --upgrade pip
pip install cyclonedx-python-lib==5.0.0  # 使用特定版本

# 或者使用 conda
conda install -c conda-forge cyclonedx-python
```

### Q2: SBOM 中缺少某些组件？

- 确保固件已正确扫描
- 检查字符串提取结果：`strings firmware.bin | grep -i freertos`
- 尝试使用 Syft（针对 Linux/ELF 固件）

### Q3: 如何验证 SBOM 合规性？

```bash
# 使用官方验证器
npm install -g @cyclonedx/cyclonedx-lint
cd project && cyclonedx-lint -i sbom.cyclonedx.json

# Python 验证
python -c "
from scanner.cyclonedx_sbom import validate_sbom
with open('sbom.cyclonedx.json') as f:
    content = f.read()
print('Valid:', validate_sbom(content))
"
```

---

## 降级模式

如果未安装 `cyclonedx-python-lib`，系统会自动切换到降级模式：

```python
# 仍会生成 JSON 文件，但不是标准 CycloneDX 格式
python test_cyclonedx.py
# ⚠️ cyclonedx-python-lib 未安装，使用降级模式
# 💡 安装命令：pip install cyclonedx-python-lib
```

降级模式的特点：
- ✅ 生成可读的 JSON 文件
- ✅ 包含基本的组件和漏洞信息
- ❌ 不符合 CycloneDX Schema 验证
- ❌ 无法被 Dependency-Track 等工具识别

---

## API 参考

### GET `/api/sbom/{task_id}`

下载任务的 SBOM。

**Query Parameters:**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| format | string | "cyclonedx" | SBOM 格式：`cyclonedx`, `syft`, `spdx` |
| schema_version | string | "1.4" | CycloneDX Schema 版本：`1.4`, `1.3` |

**响应:**
- Content-Type: `application/json`
- 文件名：`{task_id}_sbom.cyclonedx.json`

**错误码:**
- `404`: 任务不存在
- `400`: 任务未完成或无结果
- `500`: SBOM 生成失败

### GET `/api/sbom/{task_id}/validate`

验证 SBOM 合规性。

**响应:**
```json
{
  "valid": true,
  "format": "CycloneDX",
  "schema_version": "1.4",
  "component_count": 15,
  "vulnerability_count": 3,
  "message": "SBOM 格式验证通过"
}
```

---

## 下一步

1. 🔧 **集成到 CI/CD**: 在构建流水线中自动生成 SBOM
2. 📊 **监控仪表板**: 显示 SBOM 统计和趋势
3. 🔗 **依赖图可视化**: 展示组件间的依赖关系
4. 🌐 **批量导出**: 一次性导出所有任务的 SBOM

---

## 参考资料

- [CycloneDX 官方网站](https://cyclonedx.org/)
- [CycloneDX Schema 规范](https://cyclonedx.org/docs/1.4/)
- [OWASP Dependency-Track](https://dependencytrack.org/)
- [cyclonedx-python-lib 文档](https://github.com/CycloneDX/cyclonedx-python-lib)

---

**版本**: 2.1-alpha  
**最后更新**: 2026-08-04  
**维护者**: Xuanwu Team 🐢
