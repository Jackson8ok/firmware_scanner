# Bug 报告模板

---

## 🐛 问题描述

清晰简洁地描述这个 bug。

## 🔄 复现步骤

1. 打开 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

## 🎯 预期行为

你期望发生什么？

## 📸 截图

如果可以，添加截图来帮助解释你的问题。

## 🖥️ 环境信息

- **操作系统**: [e.g. Ubuntu 22.04, Windows 11, macOS 13]
- **Python 版本**: [e.g. 3.10.12]
- **FastAPI 版本**: [e.g. 0.111.0]
- **Docker 版本** (如果适用): [e.g. 24.0.5]

### Docker 环境（如果使用）

```bash
docker images | grep scanner
# 输出示例: ghcr.io/Jackson8ok/firmware_scanner   latest   abc1234   2 days ago   500MB
```

## 📋 日志信息

如果有错误日志，请粘贴相关部分：

```log
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  ...
```

## 💡 可能的解决方案

你对如何修复这个问题的想法。（可选）

## 📝 额外上下文

在此处添加有关问题的其他上下文信息。

---

**注意**: 
- 删除不适用的部分
- 提供更多细节通常会有帮助！
- 如果是 CVE 相关问题，请注明影响范围和严重程度
