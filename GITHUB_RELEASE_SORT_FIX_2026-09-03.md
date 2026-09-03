# GitHub Release 排序问题修复报告

**日期**: 2026-09-03  
**问题**: v2.6.0 Draft Release 显示在列表最上方  
**状态**: ✅ **已修复**

---

## 🐛 问题描述

用户报告 GitHub Release 列表页面排版异常：
- **预期**: v2.7.2（最新版本）显示在最上方
- **实际**: v2.6.0 Draft 版本显示在最上方

---

## 🔍 根因分析

### 问题原因

1. **存在 Draft 状态的 Release**
   - Tag: `v2.6.0`（实际为 `untagged-2ed06d9c4f9772d4d7eb`）
   - 名称：`AFVS v2.6.0 — 批量扫描队列 + 报告模板 + 邮件通知 + 版本注入`
   - 创建时间：2026-08-26T10:07:53Z
   - 状态：Draft（草稿）

2. **GitHub Release 排序规则**
   - GitHub 按 `published_at` 时间倒序排列
   - Draft Release 也会参与排序
   - 该 Draft 创建时间较晚，导致排在前面

3. **Latest Release 标记丢失**
   - v2.7.2 创建时未设置 `make_latest=true`
   - 导致没有 Release 被标记为 Latest

---

## 🔧 修复方案

### 步骤 1: 删除 Draft Release

```python
# 获取 Draft Release ID
release_id = 377039699

# 删除 Draft
DELETE /repos/{owner}/{repo}/releases/{release_id}
```

**结果**: ✅ Draft Release 已成功删除

---

### 步骤 2: 设置 v2.7.2 为 Latest Release

```python
# 获取 v2.7.2 Release ID
release_id = 381706718

# 设置为 Latest
PATCH /repos/{owner}/{repo}/releases/{release_id}
{
  "make_latest": true
}
```

**结果**: ✅ v2.7.2 已标记为 Latest Release

---

## ✅ 修复验证

### Release 列表（修复后）

| 排名 | Tag | 名称 | 状态 |
|------|-----|------|------|
| 1 | **v2.7.2** | Phase 4 SBOM 融合架构版 | 🏆 **LATEST** |
| 2 | v2.7.1 | SBOM 稳定性热修复 | ✅ |
| 3 | v2.7.0 | 组件指纹识别增强版 | ✅ |
| 4 | v2.7.0-phase3 | Phase3 - 版本未知组件优化 | 🔬 Pre-release |
| 5 | v2.7.0-phase2 | Phase2 - SBOM × 指纹一致性 | 🔬 Pre-release |
| 6 | v2.7.0-phase1 | Phase1 - 大小写不敏感修复 | 🔬 Pre-release |
| 7 | v2.6.0-fix2 | 最终修复版 | ✅ |
| 8 | v2.6.0 | 性能与功能增强版 | ✅ |

### Latest Release 验证

```
✅ Latest Release: v2.7.2
   名称：v2.7.2 - Phase 4 SBOM 融合架构版
   发布时间：2026-09-03T03:25:58Z
   URL: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.2
```

---

## 📋 经验教训

### 问题根源

1. **Draft Release 管理不当**
   - 创建 Draft 后忘记发布或删除
   - Draft Release 会影响 Release 列表排序

2. **Release 创建流程不规范**
   - 未设置 `make_latest=true`
   - 依赖 GitHub 自动判断 Latest

### 改进措施

#### 1. 规范 Release 创建流程

```bash
# 使用 GitHub CLI 创建 Release（推荐）
gh release create v2.8.0 \
  --title "v2.8.0 - WebSocket 实时推送版" \
  --notes-file RELEASE_NOTES_v2.8.0.md \
  --latest \
  --verify-tag
```

#### 2. 使用 API 时设置 Latest 标记

```python
# 创建 Release 时设置 make_latest=true
data = {
    "tag_name": "v2.8.0",
    "name": "v2.8.0 - WebSocket 实时推送版",
    "body": release_body,
    "draft": False,
    "prerelease": False,
    "make_latest": True  # ← 关键！
}
```

#### 3. 定期清理 Draft Release

```bash
# 检查是否有遗留的 Draft
gh release list --limit 100 | grep Draft

# 删除 Draft
gh release delete <tag> --cleanup-tag
```

#### 4. 创建 Release 检查清单

- [ ] Tag 已创建并推送
- [ ] Release Notes 已准备
- [ ] 设置 `draft=false`（正式发布）
- [ ] 设置 `prerelease=false`（正式版本）
- [ ] 设置 `make_latest=true`（最新版本）
- [ ] 验证 Release 页面显示正常
- [ ] 验证 Latest Release 标记正确

---

## 🎯 最佳实践

### GitHub Release 创建脚本（推荐）

```bash
#!/bin/bash
# scripts/create_release.sh

VERSION=$1
NOTES_FILE=$2

if [ -z "$VERSION" ] || [ -z "$NOTES_FILE" ]; then
    echo "用法：$0 <version> <notes_file>"
    exit 1
fi

echo "创建 Release: $VERSION"

# 1. 创建并推送 Tag
git tag -a $VERSION -m "Release $VERSION"
git push origin $VERSION

# 2. 创建 GitHub Release
gh release create $VERSION \
  --title "$VERSION" \
  --notes-file $NOTES_FILE \
  --latest \
  --verify-tag \
  --draft=false

echo "✅ Release 创建成功"
```

### Python API 脚本（自动化）

```python
#!/usr/bin/env python3
# scripts/create_github_release.py

import requests
import os

TOKEN = os.getenv('GITHUB_TOKEN')
REPO = 'Jackson8ok/afvs-auto-firmware-vulnerability-scanner'

def create_release(tag_name, name, body, make_latest=True):
    """创建 GitHub Release"""
    
    headers = {
        'Authorization': f'token {TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    data = {
        'tag_name': tag_name,
        'name': name,
        'body': body,
        'draft': False,
        'prerelease': False,
        'make_latest': make_latest
    }
    
    url = f'https://api.github.com/repos/{REPO}/releases'
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        print(f"✅ Release 创建成功：{tag_name}")
        print(f"   URL: {response.json()['html_url']}")
        return True
    else:
        print(f"❌ 创建失败：{response.status_code}")
        print(f"   响应：{response.text}")
        return False

# 使用示例
create_release(
    tag_name='v2.8.0',
    name='v2.8.0 - WebSocket 实时推送版',
    body=open('RELEASE_NOTES_v2.8.0.md').read(),
    make_latest=True
)
```

---

## 📊 影响评估

### 修复前

- ❌ Release 列表排序错误
- ❌ Latest Release 标记缺失
- ❌ 用户可能下载到旧版本

### 修复后

- ✅ Release 列表正确排序（v2.7.2 在最上方）
- ✅ Latest Release 标记正确
- ✅ 用户自动下载到最新版本

---

## 🔗 相关链接

- **Release 列表**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases
- **Latest Release**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/latest
- **v2.7.2 Release**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.2

---

**维护者**: 攻城狮阿信 [Jackson]  
**邮箱**: zhu80k@163.com  
**日期**: 2026-09-03

---

⟦ GitHub Release 排序问题修复完成｜状态：Draft 删除✅ + Latest 标记✅；下一步：规范 Release 创建流程，避免重复问题｜锚点：GitHub Release 修复，v2.7.2 Latest，Draft 清理 ⟧
