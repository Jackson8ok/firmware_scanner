# 🐢 玄武固件漏洞扫描平台 v2.4.1 发布说明

**发布日期**: 2026-08-17  
**版本**: v2.4.1  
**维护者**: 攻城狮阿信[Jackson]  
**邮箱**: zhu80k@163.com  
**许可证**: MIT

---

## 🎉 重大更新

### 🐢 品牌全面升级为「玄武」

本项目正式更名为「**玄武**」(Xuanwu)，寓意防御稳固、安全可靠，与中国古代四大神兽之一的文化内涵完美契合。

| 变更项 | 旧名称 | 新名称 |
|--------|--------|--------|
| 项目名称 | PokeClaw | 玄武/Xuanwu |
| Logo Emoji | 🦞 (龙虾) | 🐢 (玄武/龟蛇合体) |
| 核心团队 | PokeClaw Team | 玄武团队 |
| 核心开发者 | Mewtwo Master | 攻城狮阿信 |

### 🗑️ 仓库全面清理

- ✅ **移除所有旧品牌引用**：PokeClaw、🦞、龙虾、Mewtwo Master 等已全部清除
- ✅ **清理历史文档**：移除 20+ 历史报告/临时文档，保留核心 README 和 DEPLOYMENT.md
- ✅ **清理无用文件**：删除 .trash、logs_test、.ipynb_checkpoints、--help 等无用目录
- ✅ **Git 历史重写**：提交历史中的旧品牌引用已全部替换为「玄武」/「攻城狮阿信」
- ✅ **删除 DVRF 固件**：移除所有 DVRF 相关文件和引用

### 🔧 其他改进

- ✅ 统一负责人标识为 `攻城狮阿信[Jackson];zhu80k@163.com`
- ✅ 统一邮箱为 `zhu80k@163.com`
- ✅ 所有文档中的品牌 emoji 统一为 🐢
- ✅ 移除过时的示例配置和测试脚本

---

## 📋 从 v2.4.0 升级

### 破坏性变更

无破坏性变更。此版本完全向后兼容。

### 迁移步骤

```bash
# 拉取最新代码
git pull origin main

# 如需重新克隆（获得干净历史）
git clone https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git
cd firmware_scanner
```

---

## 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git
cd firmware_scanner

# 安装依赖
pip install -r requirements.txt

# 启动服务
./scripts/startup.sh

# 访问 Dashboard
open http://localhost:8000
```

---

## 📦 可用版本

| 版本 | 说明 |
|-----|------|
| v1.0.0-alpha | 初始开源版本 |
| v1.0.0-beta | PDF 报告生成 + 品牌升级 |
| v2.4.0 | PDF 导出优化 + Bug 修复 |
| **v2.4.1** | **全面品牌升级 + 仓库清理** |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📜 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

## 🔗 相关链接

- **GitHub 仓库**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner
- **问题反馈**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/issues
- **安全报告**: zhu80k@163.com

---

**感谢你选择「玄武」！让我们一起构建更安全的固件世界。** 🐢

*最后更新*: 2026-08-17  
*维护者*: 攻城狮阿信 & 玄武团队
