# 🐢 手动创建 GitHub Release v2.4.2-hotfix 指南

**原因**: 当前环境未配置 GitHub API Token，需手动创建 Release

---

## 📋 步骤

### 1. 访问 GitHub Releases 页面

打开：https://github.com/Jackson8ok/firmware_scanner/releases/new

### 2. 填写 Release 信息

| 字段 | 值 |
|------|-----|
| **Tag version** | `v2.4.2-hotfix` |
| **Target** | `main` |
| **Release title** | `🐢 玄武 v2.4.2-hotfix - P0/P1 关键 Bug 修复` |

### 3. 复制 Release Notes

打开文件：`/mnt/workspace/firmware_scanner/docs/RELEASE_NOTES_v2.4.2-hotfix.md`

```bash
cat /mnt/workspace/firmware_scanner/docs/RELEASE_NOTES_v2.4.2-hotfix.md
```

**复制全部内容**，粘贴到 Release description 中。

### 4. 发布 Release

- [ ] 勾选 "Set as the latest release"
- [ ] 点击 "Publish release"

---

## ✅ 验证

发布后访问：https://github.com/Jackson8ok/firmware_scanner/releases/tag/v2.4.2-hotfix

应显示：
- ✅ Tag: v2.4.2-hotfix
- ✅ Commit: b15ecaa
- ✅ Release Notes 完整
- ✅ 5 个 Bug 修复清单
- ✅ 测试报告
- ✅ 升级指南

---

## 🔧 自动化（可选）

如需自动化创建 Release，需配置 GitHub Token：

```bash
# 1. 创建 Personal Access Token
# 访问：https://github.com/settings/tokens
# 权限：repo (Full control of private repositories)

# 2. 保存 Token
echo "ghp_xxxxxxxxxxxx" > /mnt/workspace/.github_token
chmod 600 /mnt/workspace/.github_token

# 3. 运行创建脚本
bash /tmp/create_release.sh
```

---

*创建日期：2026-08-19*  
*创建者：攻城狮阿信 [Jackson]*
