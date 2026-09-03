# PR 提交模板

---

## 🎯 目的

简要说明这个 PR 的目的和解决的问题。

### 关联 Issue

Closes #xxx  
Fixes #yyy  
Related to #zzz

## 📝 变更内容

详细说明做了哪些修改：

- [ ] 新增功能 A
- [ ] 修复 Bug B  
- [ ] 优化性能 C
- [ ] 更新文档 D

### 技术细节

```python
# 关键代码变更示例
def calculate_compliance_score(cves: List[Dict]) -> float:
    """计算合规得分的逻辑"""
    # ... 你的实现 ...
```

### UI/UX变更（如适用）

![Screenshot](url-to-screenshot.png)

**描述**: 
- 新增了 R155 评分卡片
- 添加了高级过滤功能

## 🧪 测试说明

### 如何测试

```bash
# 1. 运行单元测试
pytest tests/test_r155.py -v

# 2. 启动服务查看效果
uvicorn api.main:app --reload

# 3. 访问前端界面
open http://localhost:8000
```

### 测试用例

| 测试场景 | 预期结果 | 实际结果 |
|---------|---------|---------|
| 上传正常固件 | 成功解析 | ✅ 通过 |
| 上传损坏文件 | 返回错误 | ✅ 通过 |
| 并发扫描限制 | 最大 3 个任务 | ✅ 通过 |

### 性能对比（如适用）

```
Before: ~5 分钟/次 (100MB 固件)
After:  ~3 分钟/次 (100MB 固件)
提升:   40% ⚡
```

## ✅ 检查清单

在提交前确认以下内容：

- [ ] 代码遵循项目的代码风格规范
  ```bash
  black . --check && flake8 . && isort --check-only .
  ```
- [ ] 添加了必要的注释和文档字符串
- [ ] 更新了相关文档（README, API 文档等）
- [ ] 添加了测试用例并全部通过
  ```bash
  pytest tests/ -v --cov=.
  ```
- [ ] 没有新增任何警告信息
- [ ] 提交信息符合 Conventional Commits 规范
- [ ] PR 描述清晰完整

## 🚀 部署影响

此更改会对部署产生什么影响？

- [ ] 需要数据库迁移
- [ ] 需要新的环境变量
- [ ] 需要升级依赖包
- [ ] 无影响（向后兼容）

### 兼容性声明

- [ ] 向后兼容的破坏性变更
- [ ] 完全不兼容，需要重大版本升级

## 📸 截图/GIF（如适用）

**新功能演示：**

![New Feature Demo](path/to/screenshot.gif)

**修复前后对比：**

| Before | After |
|--------|-------|
| ![Before](before.png) | ![After](after.png) |

## 🙏 致谢

特别感谢谁帮助完成了这项工作吗？

- @username - 协助调试
- @someone - 提供灵感

## 🤔 待讨论的问题

是否有任何需要进一步讨论的问题或决策点？

1. xxx
2. yyy

---

**备注**: 
- 如果这是 WIP（进行中），请在标题前加 [WIP]
- 删除不适用的部分
- 保持 PR 专注，不要混合多个不相关的功能
