# 🔐 创建 GitHub Personal Access Token 指南

**用途**: 自动创建 Release v2.4.2-hotfix  
**耗时**: 2 分钟

---

## 📋 步骤

### 1. 访问 Token 创建页面

打开：https://github.com/settings/tokens/new

### 2. 填写信息

| 字段 | 值 |
|------|-----|
| **Note** | `firmware_scanner-release` |
| **Expiration** | `90 days` (或 No expiration) |
| **Select scopes** | ✅ `repo` (Full control of private repositories) |

### 3. 生成 Token

点击 **"Generate token"**

### 4. 复制 Token

**重要**: Token 只显示一次！立即复制。

格式：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 5. 保存 Token

#### 方式 A: 手动保存
```bash
# 替换 YOUR_TOKEN 为实际 token
echo "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" > /mnt/workspace/.github_token
chmod 600 /mnt/workspace/.github_token
```

#### 方式 B: 告诉我 token
直接回复我 token，我会自动保存并创建 Release。

---

## ✅ 验证

```bash
# 测试 token 是否有效
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# 应返回你的 GitHub 用户信息
```

---

## 🚀 自动创建 Release

Token 保存后，执行：

```bash
bash /tmp/create_release.sh
```

或告诉我"token 已保存"，我会自动执行。

---

## 🔒 安全提示

- Token 存储在 `/mnt/workspace/.github_token`（持久化目录）
- 权限设置为 `600`（仅所有者可读写）
- 90 天后过期，需重新生成
- 不要将 token 提交到 Git 仓库（已在 .gitignore 中）

---

*创建日期：2026-08-19*  
*创建者：攻城狮阿信 [Jackson]*
