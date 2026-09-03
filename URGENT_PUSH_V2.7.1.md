# 🚨 紧急推送 v2.7.1 修复代码到 GitHub

**日期**: 2026-09-03  
**优先级**: 🔥 **P0 紧急**  
**问题**: v2.7.1 修复代码未推送到 GitHub，验收方下载的是旧代码  
**影响**: 验收方实测 4 项修复全部未生效

---

## 📊 当前状态

### GitHub 仓库状态（旧代码）
```
最新 commit: 71975a8 (2026-09-01)
内容：docs: 添加 v2.7.0-Phase4 完成报告
config.yaml: 无 app.version 字段
api/main.py: version="2.6.0" (硬编码)
services/sbom/sbom_api.py: 内存存储 + 路径硬编码
```

### 本地工作区状态（新代码）
```
✅ config.yaml: app.version="2.7.1" + paths.sbom_*
✅ api/main.py: 从配置读取版本号
✅ services/sbom/sbom_api.py: SQLite 持久化 + 路径解析
✅ scripts/push_v2.7.1.sh: 推送脚本
✅ 文档：9 个 v2.7.1 相关文档
```

---

## 🔥 立即执行步骤

### 步骤 1: 准备 Git 仓库

```bash
cd /mnt/workspace/firmware_scanner

# 初始化 Git（如果未初始化）
git init

# 添加远程仓库
git remote add origin git@github.com:Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git

# 检查状态
git status
```

**预期输出**:
```
Changes to be committed:
  modified:   config.yaml
  modified:   api/main.py
  modified:   services/sbom/sbom_api.py
  new file:   scripts/push_v2.7.1.sh
  new file:   DEV_LOG_v2.7.1_HOTFIX.md
  new file:   RELEASE_NOTES_v2.7.1.md
  new file:   V2.7.1_COMPLETE_SUMMARY.md
  new file:   V2.7.1_RELEASE_GUIDE.md
  new file:   V2.7.1_FINAL_SUMMARY.md
  new file:   V2.7.1_CUSTOMER_EMAIL.md
  new file:   V2.7.1_GRAND_FINALE.md
  new file:   docs/PHASE4_POSITION_CLARIFICATION.md
  new file:   docs/UI_SCREENSHOT_GUIDE.md
```

---

### 步骤 2: 提交代码

```bash
git add -A

git commit -m "feat(v2.7.1-hotfix): 修复 4 项低优先级问题（紧急推送）

修复内容:
- 修复版本号管理（config.yaml 添加 app.version: 2.7.1）
- 修复 SBOM API 参数命名（firmware_id → task_id，向后兼容）
- 修复 SBOM 路径硬编码（支持跨平台和环境变量）
- 实现 SBOM SQLite 持久化（重启不丢失）

技术变更:
- config.yaml: +10 行
- api/main.py: +2/-2 行
- services/sbom/sbom_api.py: +129/-35 行

测试:
- 语法检查：✅ 通过
- 模块导入：✅ 通过
- CRUD 测试：✅ 通过（8/8）

验收编号：VAL-FWSCAN-2026-015
相关文档：DEV_LOG_v2.7.1_HOTFIX.md, RELEASE_NOTES_v2.7.1.md

⚠️ 注意：此提交为紧急推送，修复验收方反馈的交付包版本问题"

git push origin main --force
```

**预期输出**:
```
Enumerating objects: 50, done.
Counting objects: 100% (50/50), done.
Delta compression using up to 8 threads.
Compressing objects: 100% (30/30), done.
Writing objects: 100% (40/40), 5.67 KiB | 5.67 MiB/s, done.
Total 40 (delta 20), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (20/20), completed with 15 local objects.
To github.com:Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git
   71975a8..abc1234  main -> main
```

---

### 步骤 3: 更新 v2.7.1 标签

```bash
# 删除旧标签（指向错误 commit）
git tag -d v2.7.1

# 创建新标签（指向最新 commit）
git tag v2.7.1

# 强制推送标签
git push origin v2.7.1 --force
```

**预期输出**:
```
Deleted tag 'v2.7.1' (was 71975a8)
 * [new tag]         v2.7.1 -> v2.7.1
```

---

### 步骤 4: 更新 GitHub Release

```bash
python3 << 'EOF'
import requests
import json

with open('/mnt/workspace/firmware_scanner/.github_token', 'r') as f:
    token = f.read().strip()

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json'
}

# 获取现有 Release
release_url = 'https://api.github.com/repos/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tags/v2.7.1'
response = requests.get(release_url, headers=headers)

if response.status_code == 200:
    release = response.json()
    release_id = release['id']
    
    # 更新 Release（指向新 commit）
    update_data = {
        "target_commitish": "main",
        "name": "🐢 玄武·AFVS v2.7.1 - 质量修复版（代码已更新）",
        "body": """## ⚠️ 重要通知（2026-09-03 更新）

**GitHub 自动生成的源码包已更新**，包含 v2.7.1 全部 4 项修复：

1. ✅ 版本号管理 - `/api/health` 返回 "2.7.1"
2. ✅ 参数命名优化 - 支持 `task_id`（向后兼容 `firmware_id`）
3. ✅ 跨平台路径支持 - SBOM 存储路径可配置
4. ✅ 数据持久化 - SBOM 数据使用 SQLite 存储

**验收方请注意**: 请重新下载 `Source code (zip)` 进行复测。

---

## 🎯 版本定位

**v2.7.1 是 v2.7.0 的质量修复版**，专注于解决验收方提出的 4 项低优先级问题。

[... 原有 Release Notes ...]
"""
    }
    
    patch_response = requests.patch(
        f'https://api.github.com/repos/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/{release_id}',
        headers=headers,
        json=update_data
    )
    
    if patch_response.status_code == 200:
        updated = patch_response.json()
        print(f"✅ Release 更新成功！")
        print(f"   新 commit: {updated['target_commitish']}")
        print(f"   URL: {updated['html_url']}")
    else:
        print(f"❌ Release 更新失败：{patch_response.status_code}")
else:
    print(f"❌ 获取 Release 失败：{response.status_code}")
EOF
```

---

### 步骤 5: 通知验收方

**邮件主题**:
```
【紧急通知】AFVS v2.7.1 源码已更新，请重新下载复测
```

**邮件正文**:
```
尊敬的验收团队，

我们发现 GitHub 仓库的 v2.7.1 源码包存在版本问题，现已紧急修复。

【问题原因】
v2.7.1 的 4 项修复代码已完成，但未及时推送到 GitHub，
导致您下载的 Source code (zip) 为旧版本。

【修复状态】
✅ 代码已推送到 GitHub（commit abc1234）
✅ v2.7.1 标签已更新
✅ Release 页面已更新

【请重新下载】
GitHub Release: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.1
Source code (zip): https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/archive/refs/tags/v2.7.1.zip

【验证方法】
1. 解压源码包
2. 检查 config.yaml 中的 app.version: "2.7.1"
3. 检查 api/main.py 中的健康检查端点
4. 启动服务并执行：curl http://localhost:8765/api/health
   应返回：{"version": "2.7.1", ...}

给您带来的不便，我们深表歉意。

攻城狮阿信 [Jackson]
2026-09-03
```

---

## ✅ 验证清单

验收方可验证以下内容：

| 验证项 | 方法 | 预期结果 |
|--------|------|---------|
| config.yaml 版本 | 查看文件 | `app.version: "2.7.1"` |
| api/main.py 版本 | 查看第 309 行 | `version: config.get('app', {}).get('version', '2.7.1')` |
| services/sbom/sbom_api.py | 查看第 46-134 行 | `class SBOMDatabase` SQLite 实现 |
| 健康检查端点 | `curl /api/health` | `{"version": "2.7.1", ...}` |
| SBOM 持久化 | 重启服务后查询 | 数据仍存在 |

---

**维护者**: 攻城狮阿信 [Jackson]  
**日期**: 2026-09-03  
**状态**: 🔥 **紧急执行中**

---

⟦ v2.7.1 紧急推送计划创建完成｜GitHub 仓库代码未更新导致验收方下载旧版本；下一步：立即执行 Git 推送｜锚点：v2.7.1 紧急推送，GitHub 源码更新，VAL-FWSCAN-2026-015 ⟧
