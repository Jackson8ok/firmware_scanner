# 📋 下周工作计划 (W3 - 2026)

**周期**: 2026-08-05 ~ 2026-08-11  
**负责人**: 攻城狮阿信 (Jackson)  
**目标**: 完成 WebSocket 实时通知集成 + 启动新功能开发

---

## 🎯 本周核心目标

### P0 - 必须完成 (Critical)
1. ✅ **WebSocket 完整集成** - 与扫描队列深度整合
2. ✅ **前端自动订阅机制** - 无需手动刷新
3. ✅ **断线重连 UI 提示** - 用户体验优化

### P1 - 重要功能 (Important)
4. [ ] 组件依赖关系可视化 (D3.js)
5. [ ] Webhook 回调支持
6. [ ] 智能搜索增强

### P2 - 锦上添花 (Nice to have)
7. [ ] 错误日志聚合分析
8. [ ] 批量操作确认对话框
9. [ ] 快捷键自定义配置

---

## 📅 每日任务分配

### Monday (8/5) - WebSocket 集成 Day

#### 上午 (9:00 - 12:00)
- [ ] 修改 `scanner/task_queue.py`
  - 在扫描循环中添加 `notify_task_progress()` 调用
  - 在任务完成时调用 `notify_task_status()`
  - 错误处理时调用 `notify_scan_error()`

#### 下午 (14:00 - 18:00)
- [ ] 修改 `api/main.py`
  - 扫描完成后自动推送结果
  - 队列状态变更时广播更新
- [ ] 创建集成测试脚本
  - `tests/test_websocket_integration.py`

#### 晚上 (可选)
- [ ] 调试和性能优化
- [ ] 编写技术文档

**预期产出**: WebSocket 实时通知功能可用

---

### Tuesday (8/6) - 前端体验优化

#### 上午
- [ ] 实现前端自动订阅
  ```javascript
  // 当任务创建后自动订阅
  async function handleSingleScan() {
      const taskId = await startScan();
      subscribeToTask(taskId); // 自动订阅
  }
  ```
- [ ] 添加连接状态指示器
  - 右上角显示 WebSocket 状态 (🟢/🟡/🔴)
  - 断线时显示重连倒计时

#### 下午
- [ ] 优化任务列表 UI
  - 实时进度条动画
  - 任务完成时的庆祝效果
  - 失败任务的错误详情展开

#### 晚上
- [ ] 跨浏览器测试 (Chrome, Firefox, Safari, Edge)
- [ ] 移动端适配检查

**预期产出**: 前端交互流畅，用户体验良好

---

### Wednesday (8/7) - D3.js 可视化

#### 上午
- [ ] 研究 D3.js 最佳实践
- [ ] 设计组件依赖图数据模型
  ```javascript
  const componentData = {
    nodes: [
      { id: "FreeRTOS", type: "rtos", version: "10.4.6" },
      { id: "lwIP", type: "network", version: "2.1.3" }
    ],
    links: [
      { source: "lwIP", target: "FreeRTOS", type: "depends_on" }
    ]
  };
  ```

#### 下午
- [ ] 实现基础力导向图
- [ ] 添加交互功能
  - 节点拖拽
  - 缩放和平移
  - 点击查看详情

#### 晚上
- [ ] 性能优化 (虚拟 DOM, 按需渲染)
- [ ] 响应式适配

**预期产出**: 组件依赖关系可视化雏形

---

### Thursday (8/8) - Webhook 支持

#### 上午
- [ ] 设计 Webhook 配置界面
  - URL 配置
  - 触发事件选择
  - 重试策略设置

#### 下午
- [ ] 实现后端 Webhook 发送逻辑
  ```python
  async def send_webhook(event_type: str, payload: dict):
      for webhook in config.webhooks:
          await requests.post(
              webhook.url,
              json={"event": event_type, "data": payload},
              headers={"Authorization": f"Bearer {webhook.secret}"}
          )
  ```
- [ ] 添加签名验证
- [ ] 失败重试机制

#### 晚上
- [ ] 编写 Webhook 使用文档
- [ ] 准备示例代码 (Python, Node.js)

**预期产出**: Webhook 功能完整可用

---

### Friday (8/9) - 智能搜索增强

#### 上午
- [ ] 分析现有搜索功能瓶颈
- [ ] 实现模糊匹配算法
  ```javascript
  function fuzzySearch(query, items) {
      return items.filter(item => 
          levenshteinDistance(query.toLowerCase(), item.name.toLowerCase()) < 2
      );
  }
  ```

#### 下午
- [ ] 添加搜索结果高亮
- [ ] 实现语音搜索 (Web Speech API)
- [ ] 搜索历史记录保存

#### 晚上
- [ ] 搜索性能基准测试
- [ ] 用户体验测试

**预期产出**: 搜索功能显著改进

---

### Saturday (8/10) - 测试与文档

#### 全天
- [ ] 编写单元测试
  - WebSocket 消息格式测试
  - 前端组件渲染测试
  - 边界情况测试
- [ ] 更新所有相关文档
- [ ] 录制功能演示视频
- [ ] 准备发布说明草稿

---

### Sunday (8/11) - 复盘与规划

#### 上午
- [ ] 本周工作总结
- [ ] 问题回顾与分析
- [ ] 性能指标收集

#### 下午
- [ ] 下周工作计划制定
- [ ] 技术债务清理清单
- [ ] 团队同步会议准备

---

## 🔧 具体实施步骤

### WebSocket 集成细节

#### 1. 修改 task_queue.py

```python
# scanner/task_queue.py

from websocket_server import (
    notify_task_progress,
    notify_task_status,
    notify_scan_error
)

class ScanTask:
    async def execute(self):
        # 开始扫描
        self.status = TaskStatus.RUNNING
        await notify_task_status(self.id, 'running')
        
        # 提取阶段
        await self.extract_firmware()
        await notify_task_progress(self.id, 30, "正在提取固件...")
        
        # 扫描阶段
        await self.scan_vulnerabilities()
        await notify_task_progress(self.id, 70, "正在检测漏洞...")
        
        # R155 检查
        await self.check_r155_compliance()
        await notify_task_progress(self.id, 90, "正在生成报告...")
        
        # 完成
        self.status = TaskStatus.COMPLETED
        await notify_task_status(self.id, 'completed', self.result)
        await notify_task_progress(self.id, 100, "扫描完成！")
```

#### 2. 前端自动订阅

```javascript
// frontend/static/websocket-client.js

class WebSocketManager {
    // 新增：订阅最新任务
    subscribeLatestTask() {
        const urlParams = new URLSearchParams(window.location.search);
        const taskId = urlParams.get('task');
        
        if (taskId) {
            this.subscribe(taskId);
            console.log(`✅ 已自动订阅任务：${taskId}`);
        }
    }
    
    // 绑定到页面加载
    init() {
        super.init();
        
        // 延迟执行，确保 DOM 就绪
        setTimeout(() => {
            this.subscribeLatestTask();
        }, 2000);
    }
}
```

#### 3. 连接状态指示器

```html
<!-- 添加到 index.html -->
<div id="wsStatusIndicator" style="
    position: fixed;
    top: 20px;
    right: 180px;
    z-index: 1001;
    display: flex;
    align-items: center;
    gap: 8px;
    background: white;
    padding: 8px 12px;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    font-size: 12px;
">
    <span id="wsStatusDot" style="
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #ccc;
        animation: pulse 2s infinite;
    "></span>
    <span id="wsStatusLabel">连接中...</span>
</div>

<style>
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.ws-status-connected { background: #28a745 !important; }
.ws-status-connecting { background: #ffc107 !important; }
.ws-status-disconnected { background: #dc3545 !important; }
</style>
```

```javascript
// 在 WebSocket 客户端中更新状态
websocketManager.on('onConnected', () => {
    updateWsStatus('connected', '已连接');
});

websocketManager.on('onDisconnected', () => {
    updateWsStatus('disconnected', '已断开');
});

function updateWsStatus(state, text) {
    const dot = document.getElementById('wsStatusDot');
    const label = document.getElementById('wsStatusLabel');
    
    if (dot && label) {
        dot.className = '';
        dot.classList.add(`ws-status-${state}`);
        label.textContent = text;
    }
}
```

---

## 📊 成功标准

### WebSocket 功能
- [x] 新建任务后 1 秒内收到第一条进度消息
- [x] 断线后 3 秒内自动重连成功
- [x] 100 个并发连接下稳定运行
- [x] 消息延迟 < 200ms

### 前端体验
- [x] 无需手动刷新即可查看进度
- [x] 连接状态清晰可见
- [x] 错误提示友好易懂
- [x] 移动端触摸操作流畅

### 代码质量
- [x] 单元测试覆盖率 > 80%
- [x] ESLint 无警告
- [x] 文档完整清晰
- [x] 性能测试通过

---

## 🚨 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| WebSocket 兼容性问题 | 中 | 高 | 降级到轮询方案 |
| 前端性能下降 | 低 | 中 | 懒加载 + 虚拟化 |
| 内存泄漏 | 低 | 高 | 定期监控 + 对象池 |
| 浏览器限制 | 中 | 中 | 多协议回退 |

---

## 📦 交付物清单

### 本周必须交付
1. ✅ WebSocket 服务器 (`websocket_server.py`)
2. ✅ 前端客户端 (`websocket-client.js`)
3. ✅ 集成文档 (`docs/WEBSOCKET_INTEGRATION.md`)
4. ✅ 测试脚本 (`tests/test_websocket_integration.py`)

### 可选交付
5. ⏸️ 组件依赖图可视化
6. ⏸️ Webhook 管理界面
7. ⏸️ 智能搜索增强版

---

## 💡 创新点子收集

欢迎贡献以下方向的创意：

1. **AI 辅助修复建议**
   - 基于历史数据的修复方案推荐
   - 自动化 PR 生成

2. **区块链存证**
   - 扫描结果上链，保证不可篡改
   - 供应链审计溯源

3. **AR 可视化**
   - 手机扫描设备显示漏洞信息
   - 3D 组件关系图

4. **游戏化元素**
   - 安全评分排行榜
   - 成就系统

---

## 🤝 团队协作

### 每日站会 (Daily Standup)
- **时间**: 每天 9:30 AM
- **时长**: 15 分钟
- **内容**:
  1. 昨天完成了什么？
  2. 今天计划做什么？
  3. 遇到了什么障碍？

### 代码审查
- **PR 模板**: 强制使用
- **审查者**: 至少 1 人批准
- **合并要求**: CI 通过 + 测试覆盖

### 沟通渠道
- 📧 Email: jackson@pokeclaw.io
- 💬 Slack: #firmware-scanner-dev
- 📱 微信: PokeClaw 开发群
- 🎥 视频会议：每周二、四 晚 8 点

---

## 📈 进度跟踪

### 燃尽图 (Burndown Chart)
```
任务剩余 (小时)
20 |*
   | *
15 |  *
   |   *
10 |    *
   |     *
 5 |      *
   |       *
 0 +--------→ 天数
   1 2 3 4 5 6 7
```

### 完成率目标
- Monday: 20%
- Tuesday: 40%
- Wednesday: 60%
- Thursday: 80%
- Friday: 95%
- Weekend: 100%

---

## 🎉 庆祝里程碑

### 本周小目标达成
- ✅ WebSocket 基础框架完成 → 🍺 请自己喝杯咖啡
- ✅ 实时通知功能上线 → 🍰 买个蛋糕庆祝
- ✅ v2.4 版本发布 → 🎊 团队聚餐

---

**最后更新**: 2026-08-05  
**维护者**: 攻城狮阿信 (Jackson) 🦞  
**状态**: 🔄 进行中

<!-- ⟞ W3 工作计划创建完成，详细到每日任务 ⟟ -->
