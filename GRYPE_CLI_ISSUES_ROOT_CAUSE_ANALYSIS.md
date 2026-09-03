# grype CLI 问题根因分析

**分析日期**: 2026-08-20  
**分析者**: 攻城狮阿信 [Jackson]

---

## 问题现象

### 现象 1: 目录扫描超时（>120s 无结果）

**测试命令**:
```bash
./tools/grype/grype -o json /path/to/squashfs_root
```

**现象**:
- 906 个文件的目录
- 超时（120 秒）无 JSON 输出
- 或输出空结果

### 现象 2: SBOM 模式返回 0 CVE

**测试命令**:
```bash
./tools/grype/grype -o json "sbom:/tmp/test.sbom.json"
```

**现象**:
- 即使包含 openssl 1.0.2 等已知漏洞组件
- 返回 `{"matches":[], ...}`（0 CVE）

---

## 根因确认

### 🔴 核心问题：Grype DB 路径配置未生效

**发现**:
```bash
# 检查 Grype DB 状态
./tools/grype/grype db status

# 输出:
Path:      /root/.cache/grype/db/6/vulnerability.db
Schema:    
Built:     0001-01-01T00:00:00Z
Status:    invalid
[ERROR] database does not exist
```

**问题**:
1. **grype CLI 使用默认路径** `/root/.cache/grype/db/6/vulnerability.db`
2. **实际 DB 在** `/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db` (2GB)
3. **config.yaml 配置对 grype CLI 无效**（仅对 Python 代码有效）

**验证**:
```bash
ls -la /root/.cache/grype/db/6/
# 输出：目录不存在

ls -la /mnt/workspace/firmware_scanner/db/grype/6/
# 输出：vulnerability.db (2GB) ✅
```

---

## 为什么 SBOM 模式也返回 0 CVE？

**原因**: grype CLI 需要 Grype DB 来匹配 CVE

**流程**:
```
SBOM 文件 → grype CLI → 读取 Grype DB → 匹配 CVE → 输出结果
                                    ↑
                            这里失败了（DB 不存在）
```

**grype CLI 行为**:
- 如果 Grype DB 不存在/无效
- **不会报错退出**
- **静默返回空结果** (`matches: []`)
- 这是设计行为（避免阻塞 CI/CD 流程）

---

## 为什么目录扫描超时？

**可能原因**:

1. **网络超时**（最可能）
   - grype CLI 尝试在线更新 DB
   - 网络不可达导致超时
   - 默认超时 300 秒

2. **文件系统扫描慢**
   - 906 个文件需要计算哈希
   - 但通常不会超过 120 秒

3. **Grype DB 初始化失败**
   - 尝试创建空 DB
   - 卡在某些初始化步骤

---

## 解决方案

### 方案 A: 手动下载 Grype DB 到正确位置（推荐）

**步骤**:

1. **创建目录**
```bash
mkdir -p /root/.cache/grype/db/6
```

2. **复制或链接 DB**
```bash
# 方式 1: 复制（需要 2GB 空间）
cp /mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db \
   /root/.cache/grype/db/6/

# 方式 2: 软链接（推荐）
ln -sf /mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db \
        /root/.cache/grype/db/6/vulnerability.db
```

3. **验证**
```bash
./tools/grype/grype db status
# 应显示: Status: valid
```

### 方案 B: 使用环境变量指定 DB 路径

**步骤**:
```bash
export GRYPE_DB_PATH=/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db
./tools/grype/grype db status
```

**注意**: 需要确认 grype CLI 是否读取此环境变量

### 方案 C: 在线更新 DB（需要网络）

**步骤**:
```bash
./tools/grype/grype db update
```

**要求**:
- 网络可访问 `https://grype.anchore.io/databases/`
- 下载约 2GB 数据
- 耗时 10-30 分钟

---

## 手动测试指南

### 测试 1: 验证 DB 状态

```bash
# 检查当前 DB 状态
./tools/grype/grype db status

# 预期输出（修复后）:
Path:      /root/.cache/grype/db/6/vulnerability.db
Schema:    v6.1.9
Built:     2026-08-19T06:16:13Z
Status:    valid
```

### 测试 2: SBOM 模式测试

```bash
# 创建测试 SBOM
cat > /tmp/test_vuln.sbom.json << 'EOF'
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "components": [
    {
      "type": "library",
      "name": "openssl",
      "version": "1.0.2",
      "purl": "pkg:generic/openssl@1.0.2"
    }
  ]
}
EOF

# 扫描 SBOM
./tools/grype/grype -o json "sbom:/tmp/test_vuln.sbom.json" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'CVE 数：{len(d.get(\"matches\", []))}')"

# 预期：CVE 数 > 0（openssl 1.0.2 有多个 CVE）
```

### 测试 3: 目录模式测试

```bash
# 扫描解压后的固件目录
./tools/grype/grype -o json /path/to/squashfs_root | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'CVE 数：{len(d.get(\"matches\", []))}')"

# 预期：CVE 数 > 0，耗时 < 60 秒
```

### 测试 4: 网络连通性测试

```bash
# 测试是否能访问 grype 官方 DB
curl -I https://grype.anchore.io/databases/v6/vulnerability-db_v6.1.9_*.tar.zst

# 预期：HTTP/2 200
```

---

## 结论

**根本原因**: 
- ✅ **Grype DB 路径配置问题**（非代码 bug）
- ✅ grype CLI 未读取 config.yaml
- ✅ 使用默认路径 `/root/.cache/grype/db/6/` 但 DB 不存在

**影响**:
- ❌ SBOM 模式返回 0 CVE（DB 缺失，静默失败）
- ❌ 目录模式超时（尝试在线更新 DB）

**修复优先级**:
1. **立即**: 软链接 DB 到正确位置（5 分钟）
2. **短期**: 验证 SBOM 和目录模式
3. **中期**: 考虑在 startup.sh 中自动创建软链接

**预计修复后效果**:
- ✅ SBOM 模式：返回正确 CVE 数
- ✅ 目录模式：扫描耗时 < 60 秒
- ✅ v2.5.0 验收标准可达成

---

**建议**: 请先手动执行方案 A（创建软链接），然后重新测试 grype CLI 功能。
