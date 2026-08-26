# AFVS v2.6.0 开发日志 - Phase 6: 前端版本号自动注入

**版本**: v2.6.0  
**阶段**: Phase 6/6  
**日期**: 2026-08-26  
**状态**: ✅ 完成  
**工时**: 1 小时

---

## 📋 开发目标

解决前端页面版本号滞后问题 — 通过从后端 `/api/health` 获取版本号并动态注入到页面，
取代硬编码在 HTML/JS 中的静态版本号。

### 背景

**问题**: v2.5.4 时，发现 `/api/health` 返回 `2.5.5` 版本，但前端页面
(`frontend/templates/index.html`) 仍显示 `v2.5.4`，版本号不一致。
用户看到的是过时版本号。

**根因**: 版本号在多个地方硬编码 (`index.html` 标题/Footer、`app.js` 查询字符串、
`main.py` health 端点)，升级时容易遗漏。

### 验收标准

- [x] 前端页面从 `/api/health` 动态获取版本号
- [x] 所有显示版本号的地方自动更新
- [x] 失败降级（保留默认值）
- [x] 去除了 index.html 中的硬编码版本号
- [x] 后端 `/api/health` 返回 `2.6.0`

---

## 🎯 实现内容

### 1. 前端修改 (`frontend/static/app.js`)

**新增函数**: `injectVersion()`

```javascript
async function injectVersion() {
    try {
        const resp = await fetch('/api/health', { cache: 'no-store' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        const version = data.version || 'v2.6.0';
        
        // 注入三个位置
        const appVersionEl = document.getElementById('app-version');
        const footerVersionEl = document.getElementById('footer-version');
        const titleEl = document.querySelector('title');
        
        if (appVersionEl) appVersionEl.textContent = version;
        if (footerVersionEl) footerVersionEl.textContent = version;
        if (titleEl) titleEl.textContent = `🐢 玄武·AFVS - ... ${version}`;
        
    } catch (err) {
        console.warn('⚠️ 版本号注入失败，使用默认值:', err);
    }
}
```

**调用时机**: 在 `DOMContentLoaded` 中调用 `injectVersion()`

### 2. 前端模板修改 (`frontend/templates/index.html`)

**修改前**:
```html
<title>... v2.5.4</title>
<p class="subtitle">... | v2.2 Dashboard 增强版</p>
<p>&copy; 2026 ... | v2.5.4</p>
```

**修改后**:
```html
<title>🐢 玄武·AFVS - 汽车固件漏洞扫描器</title>
<p class="subtitle">... | <span id="app-version">v2.6.0</span></p>
<p>&copy; 2026 ... | <span id="footer-version">v2.6.0</span></p>
```

### 3. 后端修复 (`api/main.py`)

**修改**:
```python
# 修复前
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "2.5.5", ...}

# 修复后
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "2.6.0", ...}
```

同时修复 FastAPI 应用创建处的版本号:
```python
# app = FastAPI(title="AFVS API", version="2.6.0")
```

---

## ✅ 效果

| 情况 | v2.5.4 之前 | v2.6.0 之后 |
|------|-------------|-------------|
| 前端显示 | 硬编码 v2.5.4 | 动态获取 v2.6.0 |
| 后端 `/api/health` | 返回 2.5.5 | 返回 2.6.0 |
| 一致性 | ❌ 不一致 | ✅ 一致 |
| 升级时维护 | 需改 3+ 处 | 仅改 1 处 (`/api/health`) |

---

**记录人**: 攻城狮阿信 [Jackson]  
**最后更新**: 2026-08-26
