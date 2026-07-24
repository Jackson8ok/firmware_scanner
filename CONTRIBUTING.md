# 🤝 贡献指南

首先，感谢你愿意为 PokeClaw 固件漏洞扫描平台贡献力量！🙏

我们欢迎任何形式的贡献，包括 bug 修复、功能开发、文档改进、翻译等。无论你是新手还是资深开发者，都欢迎参与！

---

## 📚 目录

- [如何报告问题](#报告问题)
- [如何提交代码](#提交代码)
- [开发环境设置](#开发环境)
- [代码规范](#代码规范)
- [提交信息格式](#提交信息格式)
- [常见问题](#常见问题)

---

## 🐛 报告问题

### Bug 报告

如果你发现了 Bug，请创建一个 Issue，并包含以下信息：

1. **标题** - 简洁描述问题
2. **环境信息**
   - 操作系统版本
   - Python 版本
   - 依赖包版本
3. **复现步骤** - 详细列出如何重现问题
4. **预期行为** - 应该发生什么
5. **实际行为** - 实际发生了什么
6. **截图/日志** - 相关截图或错误日志
7. **可能的解决方案**（可选）

示例：
```markdown
## Bug: R155 合规检查在某些情况下返回空结果

### 环境
- OS: Ubuntu 22.04
- Python: 3.10.12
- fastapi: 0.111.0

### 复现步骤
1. 上传一个特定格式的固件文件
2. 运行 R155 合规检查
3. 观察返回结果为空

### 预期行为
应该返回合规检查结果

### 实际行为
返回 `{ "compliance_score": null }`

### 附加信息
固件类型：squashfs, 大小：~50MB
```

### 功能建议

如果你有新功能想法，请先在 [Discussions](https://github.com/pokeclaw/scanner/discussions) 中讨论，确认有价值后再创建 Feature Request。

---

## 💻 提交代码

### Fork & Clone

```bash
# 1. Fork 本项目到你的 GitHub 账号
# 点击页面右上角的 "Fork" 按钮

# 2. Clone 到你的本地机器
git clone https://github.com/YOUR_USERNAME/scanner.git
cd scanner

# 3. 添加上游仓库（方便同步更新）
git remote add upstream https://github.com/pokeclaw/scanner.git

# 4. 验证远程仓库
git remote -v
# origin    https://github.com/YOUR_USERNAME/scanner.git (fetch)
# origin    https://github.com/YOUR_USERNAME/scanner.git (push)
# upstream  https://github.com/pokeclaw/scanner.git (fetch)
# upstream  https://github.com/pokeclaw/scanner.git (push)
```

### 分支管理

我们采用以下分支策略：

| 分支 | 用途 | 保护规则 |
|------|------|---------|
| `main` | 生产环境代码 | ✅ 禁止直接推送<br>✅ 必须 PR + Review<br>✅ 必须通过 CI |
| `develop` | 开发分支 | ✅ PR + Review |
| `feature/*` | 新功能开发 | - |
| `bugfix/*` | Bug 修复 | - |
| `hotfix/*` | 紧急修复 | ⚡ 可直接推送 main |

### 开发流程

```bash
# 1. 从 develop 分支创建新分支
git checkout develop
git pull upstream develop
git checkout -b feature/amazing-feature

# 2. 开始编码...

# 3. 确保代码通过本地测试
pytest tests/ -v
black . --check
flake8 .

# 4. 提交更改
git add .
git commit -m "feat: 添加令人印象深刻的功能"

# 5. 推送到你的远程分支
git push origin feature/amazing-feature

# 6. 创建 Pull Request
# 访问 https://github.com/YOUR_USERNAME/scanner/pulls
# 点击 "Compare & pull request"
# 选择 base 分支为 `develop`
# 填写详细的 PR 描述
```

---

## 🛠️ 开发环境设置

### 前置要求

- Python 3.8+
- Git
- Binwalk（固件分析工具）
- Docker（可选，用于容器化开发）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/scanner.git
cd scanner

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装开发依赖
pip install black flake8 pytest pytest-cov mypy isort

# 5. 安装 Git hooks（可选）
cp scripts/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit

# 6. 配置环境变量
cp config.yaml.example config.yaml
# 编辑 config.yaml 填入你的配置

# 7. 启动开发服务器
uvicorn api.main:app --reload --port 8000

# 8. 访问 http://localhost:8000/docs
```

### 依赖说明

```yaml
# 系统级依赖（部分系统需要手动安装）
Ubuntu/Debian:
  sudo apt-get install binwalk squashfs-tools p7zip-full

macOS:
  brew install binwalk p7zip

Windows:
  - 使用 WSL 或 Docker 开发
```

---

## 📝 代码规范

### Python 代码风格

我们遵循 [PEP 8](https://pep8.org/) 标准，并使用以下工具自动检查：

```bash
# 格式化代码
black .

# 检查导入顺序
isort .

# 代码质量检查
flake8 . --max-line-length=127

# 类型检查
mypy . --ignore-missing-imports
```

### 命名规范

```python
# 类名：大驼峰命名
class ComplianceChecker:
    pass

# 函数和变量：小写 + 下划线
def calculate_compliance_score(cves):
    component_name = "Apache Log4j"

# 常量：全大写 + 下划线
MAX_CONCURRENT_TASKS = 3
DEFAULT_TIMEOUT = 300

# 私有方法：单下划线前缀
def _internal_helper(self):
    pass

# 避免命名冲突：双下划线前缀
__avoid_conflict = True
```

### 注释和文档

所有公共类和函数必须有 docstring：

```python
def calculate_compliance_score(
    cves: List[Dict], 
    rules: Dict[str, Rule]
) -> float:
    """
    计算固件的 R155 合规得分
    
    Args:
        cves: CVE 列表，每个包含 cve_id、cvss_score 等字段
        rules: 合规规则映射，key 为 rule_id
        
    Returns:
        合规得分 (0-100)，分数越表示问题越多
        
    Raises:
        ValueError: 当输入数据格式不正确时
        
    Example:
        >>> score = calculate_compliance_score(cves_list, rules_dict)
        >>> print(f"合规得分：{score:.2f}")
    """
    pass
```

### JavaScript 代码风格

```javascript
// 函数声明使用 const + 箭头函数
const calculateScore = (a, b) => a + b;

// 异步函数使用 async/await
async function fetchCompliance(taskId) {
  const response = await fetch(`/api/compliance/${taskId}`);
  return response.json();
}

// 对象属性使用引号保持一致性
const config = {
  'baseUrl': '/api',
  'timeout': 30000
};

// 数组方法优先使用 map/filter/reduce
const scores = vulnerabilities.map(v => v.cvss_score);
```

---

## 📋 提交信息格式

我们采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 PDF 导出功能` |
| `fix` | Bug 修复 | `fix: 修复 R155 得分计算错误` |
| `docs` | 文档变更 | `docs: 更新 README 部署说明` |
| `style` | 代码格式（不影响功能） | `style: 格式化 import 语句` |
| `refactor` | 重构 | `refactor: 优化任务队列逻辑` |
| `perf` | 性能优化 | `perf: 提升数据库查询速度` |
| `test` | 添加/修改测试 | `test: 添加 R155 单元测试` |
| `chore` | 构建/工具链 | `chore: 升级依赖包版本` |
| `revert` | 回滚提交 | `revert: 回滚 feat 中的某个功能` |

### 格式

```bash
<type>(<scope>): <subject>

<body>

<footer>
```

### 示例

```bash
feat(r155): 添加高级过滤搜索功能

实现按最小扣分、规则 ID、CVE ID 进行过滤的高级搜索
支持多条件组合筛选

- 新增 R155Filter 组件
- 集成到现有 Dashboard
- 添加单元测试覆盖

Closes #123
```

```bash
fix(compliance): 修复空值导致的崩溃问题

当 compliance_scores 为空数组时，calculate_average() 会抛出异常

- 添加边界条件检查
- 默认值设置为 0
- 添加相应测试用例

Fixes #456
```

---

## 🔍 Pull Request 检查清单

提交 PR 前，请确认：

- [ ] 代码遵循项目风格规范
- [ ] 添加了必要的注释和文档字符串
- [ ] 更新了相关文档（如有）
- [ ] 添加了测试用例（如适用）
- [ ] 通过了所有本地测试
  ```bash
  pytest tests/ -v
  black --check .
  flake8 .
  ```
- [ ] 没有新增警告信息
- [ ] 提交信息符合规范
- [ ] PR 描述清晰完整

### PR 模板

```markdown
## 🎯 目的

简要说明这个 PR 的目的。

## 📝 变更内容

- [ ] 新增功能 A
- [ ] 修复 Bug B
- [ ] 优化性能 C

## 🧪 测试

说明如何测试这些变更：

```bash
# 运行测试
pytest tests/test_r155.py -v

# 启动服务查看效果
uvicorn api.main:app --reload
```

## 📸 截图（如适用）

![Demo](url-to-screenshot.png)

## 📚 相关 Issue

Closes #123

## 📋 检查清单

- [ ] 代码通过所有检查
- [ ] 已添加测试
- [ ] 已更新文档
- [ ] 无新警告
```

---

## ❓ 常见问题

### Q1: 我的 PR 多久会被 Review？

A: 通常会在 **3-5 个工作日**内收到第一次回复。如果是紧急修复，可以在 Issue 中 @maintainers。

### Q2: 如何保持分支与主仓库同步？

```bash
# 定期同步上游 develop 分支
git fetch upstream
git merge upstream/develop

# 或者使用 rebase（更干净的提交历史）
git rebase upstream/develop
```

### Q3: 提交后发现了 Bug 怎么办？

A: 直接针对同一个 PR 继续提交新的 commit，并在消息中说明修正内容：

```bash
fix: 修正上一个 commit 中的拼写错误
```

### Q4: 可以一次性提交很多小改动吗？

A: 不建议。请将不同的功能拆分成多个独立的 PR，这样更容易 Review。

### Q5: 我是新手，有什么适合入门的任务吗？

A: 查看标记为 [`good first issue`](https://github.com/pokeclaw/scanner/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) 或 [`help wanted`](https://github.com/pokeclaw/scanner/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) 的 Issue。

---

## 🌟 成为核心贡献者

持续贡献且质量优秀的贡献者有机会成为核心团队成员，获得：

- 👑 Merge 权限
- 📢 项目决策参与权
- 🎖️ GitHub 组织成员身份
- 📝 作者署名权

---

## 📜 行为准则

本项目采用 [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md)。

简而言之：**尊重他人，保持专业，拥抱多样性**。

---

## 💬 需要帮助？

- 💡 [Discussions](https://github.com/pokeclaw/scanner/discussions) - 提问交流
- 🐛 [Issues](https://github.com/pokeclaw/scanner/issues) - 报告问题
- ✉️ Email: contact@pokeclaw.io

---

**感谢所有为 PokeClaw 做出贡献的人！** ❤️

<a href="https://github.com/pokeclaw/scanner/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=pokeclaw/scanner" />
</a>

Made with [contrib.rocks](https://contrib.rocks).
