# AFVS v2.7.1 补丁开发日志

**日期**: 2026-09-03  
**版本**: v2.7.1-hotfix  
**目标**: 修复验收方提出的 4 项低优先级问题  
**验收编号**: VAL-AFVS-2026-015（计划中）

---

## 📋 问题清单

| # | 问题 | 文件 | 行号 | 优先级 | 状态 |
|---|------|------|------|:------:|:----:|
| 1 | `/api/health` 返回版本号 2.6.0（应为 2.7.1） | `api/main.py` | 166, 309 | 低 | ✅ 已完成 |
| 2 | `firmware_id` 参数命名误导（实际是 task_id） | `services/sbom/sbom_api.py` | 157 | 中 | ✅ 已完成 |
| 3 | SBOM 存储路径硬编码 Linux 路径 | `services/sbom/sbom_api.py` | 137 | 中 | ✅ 已完成 |
| 4 | SBOM 存储为内存字典，重启丢失 | `services/sbom/sbom_api.py` | 46 | 中 | ✅ 已完成 |

---

## 🔧 修复方案

### 问题 1: 版本号管理

**现状**:
```python
# api/main.py 第 166 行
_base_app = FastAPI(
    title="固件漏洞扫描平台", 
    version="2.6.0",  # ❌ 硬编码
    ...
)

# 第 309 行
async def health_check():
    return {
        "status": "healthy",
        "version": "2.6.0",  # ❌ 硬编码
        ...
    }
```

**修复方案**:
```python
# 方案 A: 使用配置文件（推荐）
_base_app = FastAPI(
    title="固件漏洞扫描平台", 
    version=config.get('app', {}).get('version', '2.7.1'),
    ...
)

# 方案 B: 使用常量
__version__ = "2.7.1"
_base_app = FastAPI(
    title="固件漏洞扫描平台", 
    version=__version__,
    ...
)
```

---

### 问题 2: 参数命名误导

**现状**:
```python
# services/sbom/sbom_api.py 第 61 行
async def import_sbom(
    file: UploadFile = File(...),
    firmware_id: Optional[str] = Form(None, description="关联的固件 ID")
):
    # ❌ 参数名叫 firmware_id，但实际语义是 task_id
```

**修复方案**:
```python
# 向后兼容方式：同时支持 firmware_id 和 task_id
async def import_sbom(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(None, description="关联的扫描任务 ID"),
    firmware_id: Optional[str] = Form(None, description="[已弃用] 使用 task_id 代替")
):
    # 向后兼容
    if firmware_id and not task_id:
        task_id = firmware_id
        logger.warning("firmware_id 参数已弃用，请使用 task_id")
```

---

### 问题 3: SBOM 存储路径硬编码

**现状**:
```python
# services/sbom/sbom_api.py 第 66 行
upload_dir = Path("/mnt/workspace/firmware_scanner/uploads/sbom")
# ❌ 硬编码 Linux 路径，Windows 下会创建异常目录
```

**修复方案**:
```python
# 使用配置项 + 相对路径
from pathlib import Path
import os

# 从配置文件读取
base_dir = Path(__file__).parent.parent.parent
upload_dir = base_dir / config.get('paths', {}).get('sbom_uploads', 'uploads/sbom')

# 或使用环境变量（跨平台）
upload_dir = Path(os.getenv('SBOM_UPLOAD_DIR', str(base_dir / 'uploads' / 'sbom')))
```

---

### 问题 4: SBOM 存储为内存字典

**现状**:
```python
# services/sbom/sbom_api.py 第 41 行
_sbom_store: Dict[str, Dict] = {}
# ❌ 进程重启后数据丢失
```

**修复方案**:
```python
# 使用 SQLite 持久化
import sqlite3
from pathlib import Path

class SBOMDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sbom_records (
                sbom_id TEXT PRIMARY KEY,
                file_path TEXT,
                firmware_id TEXT,
                components JSON,
                components_count INTEGER,
                format TEXT,
                created_at TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def save(self, sbom_data: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sbom_records 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sbom_data['sbom_id'],
            sbom_data['file_path'],
            sbom_data['firmware_id'],
            json.dumps(sbom_data['components']),
            sbom_data['components_count'],
            sbom_data['format'],
            sbom_data['created_at'],
            sbom_data['status']
        ))
        conn.commit()
        conn.close()
    
    def get(self, sbom_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sbom_records WHERE sbom_id = ?', (sbom_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

# 使用
db_path = str(base_dir / 'db' / 'sbom.db')
sbom_db = SBOMDatabase(db_path)
```

---

## 📝 修复步骤

### ✅ 步骤 1: 修复版本号管理

**文件**: `api/main.py`, `config.yaml`

**修改内容**:
1. 在 `config.yaml` 中添加 `app.version: "2.7.1"`
2. 在 `api/main.py` 中从配置读取版本号
3. 更新 FastAPI 应用初始化和健康检查端点

**代码**:
```python
# config.yaml
app:
  version: "2.7.1"

# api/main.py
_base_app = FastAPI(
    title="固件漏洞扫描平台", 
    version=config.get('app', {}).get('version', '2.7.1'),
    ...
)

@_base_app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": config.get('app', {}).get('version', '2.7.1'),
        ...
    }
```

**状态**: ✅ 完成

---

### ✅ 步骤 2: 修复参数命名

**文件**: `services/sbom/sbom_api.py`

**修改内容**:
1. 添加 `task_id` 参数（推荐）
2. 保留 `firmware_id` 参数（向后兼容）
3. 添加弃用警告日志

**代码**:
```python
@sbom_router.post("/import")
async def import_sbom(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(None, description="关联的扫描任务 ID"),
    firmware_id: Optional[str] = Form(None, description="[已弃用] 使用 task_id 代替")
):
    # 向后兼容
    if firmware_id and not task_id:
        task_id = firmware_id
        logger.warning("⚠️ firmware_id 参数已弃用，请使用 task_id")
```

**状态**: ✅ 完成

---

### ✅ 步骤 3: 修复路径硬编码

**文件**: `services/sbom/sbom_api.py`, `config.yaml`

**修改内容**:
1. 在 `config.yaml` 中添加 `sbom_uploads` 配置项
2. 实现 `resolve_path()` 函数解析环境变量占位符
3. 支持跨平台路径（Windows/Linux/macOS）

**代码**:
```yaml
# config.yaml
paths:
  sbom_uploads: "${SBOM_UPLOAD_DIR:-./uploads/sbom}"
  sbom_db: "${SBOM_DB_PATH:-./db/sbom.db}"
```

```python
# services/sbom/sbom_api.py
def resolve_path(config_value: str, default_path: Path) -> Path:
    """解析配置路径（支持环境变量占位符）"""
    import re
    pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
    match = re.search(pattern, config_value)
    
    if match:
        env_name = match.group(1)
        default_value = match.group(2) if match.group(2) else ''
        resolved = os.getenv(env_name, default_value)
        if resolved:
            return Path(resolved)
    
    return Path(config_value)
```

**状态**: ✅ 完成

---

### ✅ 步骤 4: 实现 SQLite 持久化

**文件**: `services/sbom/sbom_api.py`

**修改内容**:
1. 创建 `SBOMDatabase` 类封装 SQLite 操作
2. 实现 `save()`, `get()`, `delete()`, `list_all()` 方法
3. 替换原有的内存字典 `_sbom_store`

**代码**:
```python
class SBOMDatabase:
    """SBOM SQLite 数据库（v2.7.1 新增）"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sbom_records (
                sbom_id TEXT PRIMARY KEY,
                file_path TEXT,
                task_id TEXT,
                components JSON,
                components_count INTEGER,
                format TEXT,
                created_at TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def save(self, sbom_data: Dict):
        """保存 SBOM 记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sbom_records 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (...))
        conn.commit()
        conn.close()
```

**状态**: ✅ 完成

---

### ✅ 步骤 5: 测试验证

**测试内容**:
1. ✅ 配置加载测试
2. ✅ 模块导入测试
3. ✅ 数据库初始化测试
4. ✅ CRUD 操作测试（保存/读取/删除）
5. ✅ 路径解析测试

**测试结果**:
```
✅ SBOM API 模块导入成功
✅ SBOM 数据库初始化成功
✅ SBOM 上传目录：uploads/sbom
✅ 测试数据保存成功
✅ 测试数据读取成功：test_123
✅ 测试数据清理完成

✅ 所有测试通过！v2.7.1 修复验证成功
```

**状态**: ✅ 完成

---

### ⏳ 步骤 6: 更新文档

- [ ] 更新 RELEASE_NOTES_v2.7.1.md
- [ ] 更新 API 文档
- [ ] 更新用户指南

---

## ✅ 验收标准

- [ ] `/api/health` 返回正确版本号（2.7.1）
- [ ] SBOM API 同时支持 `task_id` 和 `firmware_id`（向后兼容）
- [ ] SBOM 存储路径可配置（支持 Windows/Linux/macOS）
- [ ] SBOM 数据持久化（重启后不丢失）
- [ ] 所有现有测试通过
- [ ] 冒烟测试通过

---

**维护者**: 攻城狮阿信 [Jackson]  
**邮箱**: zhu80k@163.com

---

⟦ v2.7.1 补丁开发启动｜4 项问题已分析，修复方案已规划；下一步：执行代码修复｜锚点：v2.7.1-hotfix, 4 项修复，VAL-AFVS-2026-015 ⟧
