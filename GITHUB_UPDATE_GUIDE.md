# GitHub 仓库更新指南

**日期**: 2026-08-25  
**仓库**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner

---

## 📝 需要手动更新的内容

由于 GitHub API 需要 Token 权限，以下操作需要**在 GitHub 网页上手动完成**：

### 1. 更新仓库名称（About 部分）

**位置**: GitHub 仓库首页 → 右侧 "About" 区域 → 设置图标 ⚙️

**当前显示**:
```
firmware_scanner
```

**建议更新为**:
```
🐢 玄武·AFVS | Auto Firmware Vulnerability Scanner
```

**描述** (Website 下方):
```
汽车固件漏洞扫描器 | 已验证 8 轮客户验收 | CVE 偏差<5% | 字段完整率 100%
```

**Topics 标签**:
```
afvs
automotive-security
firmware-analysis
vulnerability-scanner
cybersecurity
supply-chain-security
```

---

### 2. 创建 v2.5.4 Release

**位置**: GitHub → Releases → Create a new release

**Tag version**: `v2.5.4` (已存在)

**Release title**:
```
🐢 AFVS v2.5.4 - 终验通过（官方下载通道开通）
```

**Description**:
```markdown
## 🎉 AFVS 品牌升级

**玄武·AFVS** (Auto Firmware Vulnerability Scanner) - 汽车固件漏洞扫描器

### ✅ 终验通过 (VAL-AFVS-2026-008)

全部 8 项验收标准达标：

| 指标 | 目标 | 实测 | 状态 |
|------|------|------|------|
| CVE 偏差率 | ≤5% | 0% | ✅ |
| 组件识别数 | ≥5 | 9 | ✅ |
| cvss 非空率 | ≥90% | 100% | ✅ |
| epss 非空率 | ≥90% | 100% | ✅ |
| date 非空率 | ≥90% | 100% | ✅ |
| 关键 CVE 命中 | ≥3/3 | 3/3 | ✅ |
| 重复记录 | 0 | 0 | ✅ |
| HEX 回归一致性 | 100% | 100% | ✅ |

### 📦 下载选项

| 类型 | 文件名 | 大小 | 推荐 |
|------|--------|------|------|
| **交付包** | `firmware_scanner-2.5.4.zip` | ~34MB | ✅ 推荐（含部署文档） |
| 源码包 | `Source code (zip)` | ~50MB | 核心代码一致 |

### 🚀 快速开始

```bash
# 下载交付包
wget https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/download/v2.5.4/firmware_scanner-2.5.4.zip

# 解压并启动
unzip firmware_scanner-2.5.4.zip
cd firmware_scanner
./scripts/startup.sh

# 访问 Web UI
open http://localhost:8765
```

### 📊 迭代历程

从 v2.4.1 (394 CVE 全错) 到 v2.5.4 (全指标达标)，历经 8 轮迭代：

- v2.4.1 → 修复 Grype DB 路径问题
- v2.4.2 → 修复 Grype v6 schema
- v2.4.3 → 比亚迪复测通过
- v2.5.0 → grype CLI 集成
- v2.5.1 → 字段补全验证
- v2.5.2 → 全部验收通过
- v2.5.3 → 交付包优化
- **v2.5.4 → 终验通过 ✅**

### 🏷️ 品牌说明

- **主品牌**: 玄武 🐢
- **子品牌**: AFVS (Auto Firmware Vulnerability Scanner)
- **中文名**: 玄武·车固扫描器
- **验收编号**: VAL-AFVS-2026-XXX

详见：[AFVS_BRAND_UPGRADE_2026-08-25.md](https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/blob/main/AFVS_BRAND_UPGRADE_2026-08-25.md)

### 📧 联系方式

- **维护者**: 攻城狮阿信 [Jackson]
- **邮箱**: zhu80k@163.com
- **仓库**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner

---

**🐢 玄武·AFVS - 汽车固件漏洞扫描专家**
```

**勾选**: ✅ Set as the latest release

---

### 3. 更新仓库网站链接（可选）

**位置**: GitHub 仓库首页 → 右侧 "About" → Website

**建议添加**:
```
https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.5.4
```

或直接使用官方文档链接（如有）。

---

## 🔧 使用 GitHub CLI（备选方案）

如果已安装 `gh` 命令行工具，可以使用以下命令：

```bash
# 更新仓库描述
gh repo edit Jackson8ok/firmware_scanner \
  --description "🐢 玄武·AFVS | 汽车固件漏洞扫描器" \
  --topics "afvs,automotive-security,firmware-analysis,vulnerability-scanner,cybersecurity"

# 创建 Release
gh release create v2.5.4 \
  --title "🐢 AFVS v2.5.4 - 终验通过" \
  --notes-file RELEASE_NOTES_v2.5.4.md \
  --latest
```

**安装 gh**:
```bash
# Ubuntu/Debian
sudo apt install gh

# 登录
gh auth login
```

---

## ✅ 检查清单

- [ ] 更新 About 区域的仓库名称
- [ ] 更新仓库描述
- [ ] 添加 Topics 标签（afvs, automotive-security 等）
- [ ] 创建 v2.5.4 Release
- [ ] 上传交付包 `firmware_scanner-2.5.4.zip`
- [ ] 设置 v2.5.4 为 latest release
- [ ] 验证下载链接可用

---

**执行人**: 攻城狮阿信 [Jackson]  
**日期**: 2026-08-25
