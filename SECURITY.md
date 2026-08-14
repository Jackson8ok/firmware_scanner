# 🔒 安全政策

感谢您对 玄武 安全的关注！我们非常重视安全问题，并承诺快速响应和处理。

---

## 📢 报告安全漏洞

如果您发现或怀疑存在**安全漏洞**，请**不要**公开创建 Issue。

### 正确做法：

1. **发送邮件至**: zhu80k@163.com
2. **包含以下信息**:
   - 漏洞类型（如 SQL 注入、XSS、认证绕过等）
   - 受影响版本
   - 复现步骤（尽可能详细）
   - 可能的影响范围
   - 建议的修复方案（如有）
3. **等待回复**: 我们将在 **48 小时**内确认收到您的报告

### 注意事项：

- ⚠️ **禁止**在生产环境中进行破坏性测试
- ⚠️ **禁止**访问或修改他人数据
- ⚠️ **禁止**利用漏洞进行未授权操作
- ✅ 请在测试环境中进行验证
- ✅ 请保持负责任的披露流程

---

## 🛡️ 我们的承诺

收到安全漏洞报告后，我们将：

1. **立即评估**漏洞的严重程度和影响范围
2. **制定修复计划**，优先考虑高危漏洞
3. **及时通知**报告者处理进展
4. **发布安全公告**，告知社区已解决的漏洞
5. **致谢贡献者**（如果您希望公开身份）

### SLA（服务级别协议）

| 严重性 | 响应时间 | 修复时间 |
|--------|---------|---------|
| **临界 (Critical)** | 24 小时内 | 72 小时内 |
| **高危 (High)** | 48 小时内 | 7 天内 |
| **中危 (Medium)** | 5 个工作日内 | 30 天内 |
| **低危 (Low)** | 10 个工作日内 | 下个版本 |

---

## 🔍 当前已知问题

我们目前已知晓以下非紧急问题，正在规划修复：

| ID | 描述 | 严重性 | 计划修复 |
|----|------|--------|---------|
| SEC-001 | 某些特殊编码可能导致解析延迟 | 低 | v1.1.0 |
| SEC-002 | API 端点缺少速率限制 | 中 | v1.2.0 |

---

## 🔄 安全更新流程

### 版本发布策略

```
主版本.x.y → 向后不兼容的重大变更 + 安全修复
x.次版本.y → 新功能 + 向后兼容的安全修复
x.y.修订版本 → Bug 修复和安全补丁
```

### 安全公告

所有安全更新都会在以下渠道发布：

- 📧 GitHub Security Advisories
- 📰 [GitHub Releases](https://github.com/Jackson8ok/firmware_scanner/releases)
- 💬 Discord 安全频道
- 🐦 Twitter (@玄武IO)

### CVE 编号

对于重要安全漏洞，我们会申请 CVE 编号，并在固定位置记录：

```
SECURITY_ADVISORIES.md  <- 查看所有安全公告
```

---

## 🎯 最佳实践建议

### 安装与部署

✅ **推荐做法**:

```bash
# 使用官方镜像
docker pull ghcr.io/Jackson8ok/firmware_scanner:latest

# 定期更新
docker pull ghcr.io/Jackson8ok/firmware_scanner:latest
docker compose up -d

# 最小权限运行
docker run --user 1000:1000 ...

# 配置环境变量加密
docker run -e DB_PASSWORD_FILE=/run/secrets/db_password ...
```

❌ **避免做法**:

```bash
# ❌ 不使用最新镜像
docker pull Jackson8ok/firmware_scanner:v0.1.0

# ❌ 以 root 运行
docker run -u root ...

# ❌ 明文暴露敏感信息
docker run -e PASSWORD="secret123" ...
```

### 配置安全

1. **更改默认密码**:
   ```yaml
   # config.yaml
   database:
     password: "your-strong-password-here"  # 不要使用默认值
   ```

2. **启用 HTTPS**:
   ```bash
   # 使用反向代理（Nginx/Caddy）
   # https://docs.nginx.com/nginx/admin-guide/security-controls/terminating-ssl-http/
   ```

3. **限制 API 访问**:
   ```yaml
   # config.yaml
   api:
     rate_limit: 100/minute
     allowed_ips:
       - "192.168.1.0/24"
   ```

4. **定期扫描依赖**:
   ```bash
   pip install safety
   safety check
   
   # 或使用 pip-audit
   pip install pip-audit
   pip-audit
   ```

### 监控和日志

```bash
# 启用详细日志
export DEBUG=false  # 生产环境务必关闭调试模式

# 定期检查日志
tail -f /app/logs/app.log | grep -i error

# 设置告警
cronjob: "0 * * * * curl -s http://localhost:8000/health | grep -q OK || send_alert"
```

---

## 🏆 漏洞赏金计划

目前，我们**暂不开启**正式的漏洞赏金计划。

但我们非常欢迎负责任的安全研究！对于发现严重安全漏洞的贡献者：

- 🏅 将在 Release Notes 中致谢
- 🎖️ 可能获得核心贡献者资格
- 🎁 其他形式的感谢（根据情况而定）

---

## 📜 许可与条款

通过向 玄武 报告安全漏洞，您同意：

1. 遵守本安全政策
2. 在得到明确授权前，不进行进一步测试
3. 配合我们的调查过程
4. 允许我们在修复后公开披露漏洞详情（可选择匿名）

---

## 🌟 致谢

感谢以下个人和组织帮助我们提高安全性：

- [Security Researcher A] - 发现 SEC-001
- [Security Researcher B] - 提供加固建议
- [Your Name Here] - 期待你的贡献！

想要加入这个列表？向我们报告一个有效的安全漏洞吧！

---

## 📞 联系方式

- **安全团队邮箱**: zhu80k@163.com
- **PGP 密钥**: [下载公钥](https://github.com/Jackson8ok/firmware_scanner/pgp-key.asc)
- **Discord**: #security 频道
- **应急响应**: zhu80k@163.com（仅用于紧急安全事件）

---

**最后更新**: 2026-07-24  
**文档版本**: 1.0  
**维护者**: 玄武 Security Team
