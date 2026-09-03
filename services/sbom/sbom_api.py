"""
SBOM API - v2.7.1-hotfix

提供 REST API 端点用于 SBOM 导入、比对和报告

端点:
    POST   /api/sbom/import             - 导入 SBOM 文件
    GET    /api/sbom/{sbom_id}          - 获取 SBOM 详情
    GET    /api/sbom/{sbom_id}/comparison - SBOM × 指纹比对报告
    DELETE /api/sbom/{sbom_id}          - 删除 SBOM

修复记录 (v2.7.1):
- ✅ 问题 2: firmware_id 参数更名为 task_id（向后兼容）
- ✅ 问题 3: 存储路径改为配置项（跨平台支持）
- ✅ 问题 4: 使用 SQLite 持久化（重启不丢失）
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
import os
import uuid
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
import yaml

try:
    from services.sbom.sbom_parser import SBOMParser, SBOMComponent, compare_sbom_with_fingerprint
    from scanner.task_queue import get_scan_queue
    SBOM_AVAILABLE = True
except ImportError as e:
    SBOM_AVAILABLE = False
    print(f"⚠️ SBOM 模块未加载：{e}")

# 创建 FastAPI Router
sbom_router = APIRouter(prefix="/api/sbom", tags=["sbom"])

# 加载配置
config_path = Path(__file__).parent.parent.parent / "config.yaml"
with open(config_path, encoding='utf-8') as f:
    config = yaml.safe_load(f)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        logger.info(f"✅ SBOM 数据库初始化完成：{self.db_path}")
    
    def save(self, sbom_data: Dict):
        """保存 SBOM 记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sbom_records 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sbom_data['sbom_id'],
            sbom_data['file_path'],
            sbom_data.get('task_id') or sbom_data.get('firmware_id'),
            json.dumps(sbom_data['components']),
            sbom_data['components_count'],
            sbom_data['format'],
            sbom_data['created_at'],
            sbom_data['status']
        ))
        conn.commit()
        conn.close()
    
    def get(self, sbom_id: str) -> Optional[Dict]:
        """获取 SBOM 记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sbom_records WHERE sbom_id = ?', (sbom_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            # 解析 JSON 字段
            if result.get('components'):
                result['components'] = json.loads(result['components'])
            return result
        return None
    
    def delete(self, sbom_id: str) -> bool:
        """删除 SBOM 记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sbom_records WHERE sbom_id = ?', (sbom_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def list_all(self, limit: int = 100) -> List[Dict]:
        """列出所有 SBOM 记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sbom_records ORDER BY created_at DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('components'):
                result['components'] = json.loads(result['components'])
            results.append(result)
        return results


# 初始化数据库（v2.7.1）
base_dir = Path(__file__).parent.parent.parent

def resolve_path(config_value: str, default_path: Path) -> Path:
    """解析配置路径（支持环境变量占位符）"""
    if not config_value:
        return default_path
    
    # 解析 ${VAR:-default} 格式
    import re
    pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
    match = re.search(pattern, config_value)
    
    if match:
        env_name = match.group(1)
        default_value = match.group(2) if match.group(2) else ''
        # 使用环境变量或默认值
        resolved = os.getenv(env_name, default_value)
        if resolved:
            return Path(resolved)
    
    # 如果没有占位符，直接返回配置值
    return Path(config_value)

# 解析 SBOM 数据库路径
db_path_config = config.get('paths', {}).get('sbom_db')
default_db_path = base_dir / 'db' / 'sbom.db'
db_path = resolve_path(db_path_config, default_db_path)
db_path.parent.mkdir(parents=True, exist_ok=True)
sbom_db = SBOMDatabase(str(db_path))
logger.info(f"SBOM 数据库路径：{db_path}")

# 获取 SBOM 上传目录（v2.7.1 修复：使用配置项 + 跨平台路径）
def get_sbom_upload_dir() -> Path:
    """获取 SBOM 上传目录（支持跨平台）"""
    # 优先使用配置项
    upload_dir_config = config.get('paths', {}).get('sbom_uploads')
    default_upload_dir = base_dir / 'uploads' / 'sbom'
    upload_dir = resolve_path(upload_dir_config, default_upload_dir)
    
    # 支持环境变量直接覆盖
    env_upload_dir = os.getenv('SBOM_UPLOAD_DIR')
    if env_upload_dir:
        upload_dir = Path(env_upload_dir)
    
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"SBOM 上传目录：{upload_dir}")
    return upload_dir


def get_sbom_parser() -> SBOMParser:
    """获取 SBOM 解析器单例"""
    return SBOMParser()


@sbom_router.post("/import")
async def import_sbom(
    file: UploadFile = File(..., description="SBOM 文件 (SPDX/CycloneDX JSON/CSV)"),
    task_id: Optional[str] = Form(None, description="关联的扫描任务 ID"),
    firmware_id: Optional[str] = Form(None, description="[已弃用] 使用 task_id 代替")
):
    """
    导入 SBOM 文件
    
    Request:
        - file: SBOM 文件
        - task_id: 关联的扫描任务 ID（推荐）
        - firmware_id: [已弃用] 向后兼容
    
    Response:
        {
            "sbom_id": "sbom_xxx",
            "components_count": 15,
            "format": "spdx-2.3",
            "status": "parsed"
        }
    """
    if not SBOM_AVAILABLE:
        raise HTTPException(status_code=503, detail="SBOM 模块不可用")
    
    # 向后兼容：支持 firmware_id 参数（v2.7.1 修复）
    if firmware_id and not task_id:
        task_id = firmware_id
        logger.warning("⚠️ firmware_id 参数已弃用，请使用 task_id")
    
    # 保存文件（v2.7.1 修复：使用配置项路径）
    upload_dir = get_sbom_upload_dir()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_name = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = upload_dir / unique_name
    
    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # 解析 SBOM
    try:
        parser = get_sbom_parser()
        components = parser.parse_file(str(file_path))
    except Exception as e:
        logger.error(f"SBOM 解析失败：{e}")
        raise HTTPException(status_code=400, detail=f"SBOM 解析失败：{str(e)}")
    
    # 存储到数据库（v2.7.1 修复：SQLite 持久化）
    sbom_id = f"sbom_{uuid.uuid4().hex[:12]}"
    sbom_data = {
        "sbom_id": sbom_id,
        "file_path": str(file_path),
        "task_id": task_id,
        "components": [comp.to_dict() for comp in components],
        "components_count": len(components),
        "format": parser._detect_format(file_path),
        "created_at": datetime.now().isoformat(),
        "status": "parsed"
    }
    
    sbom_db.save(sbom_data)
    
    logger.info(f"SBOM 导入成功：{sbom_id}, {len(components)} 个组件")
    
    return {
        "success": True,
        "sbom_id": sbom_id,
        "components_count": len(components),
        "format": sbom_data["format"],
        "status": "parsed"
    }


@sbom_router.get("/{sbom_id}")
async def get_sbom(sbom_id: str):
    """获取 SBOM 详情"""
    if not SBOM_AVAILABLE:
        raise HTTPException(status_code=503, detail="SBOM 模块不可用")
    
    sbom_data = sbom_db.get(sbom_id)
    
    if not sbom_data:
        raise HTTPException(status_code=404, detail="SBOM 不存在")
    
    return {
        "success": True,
        "sbom": sbom_data
    }


@sbom_router.get("/{sbom_id}/comparison")
async def get_comparison(sbom_id: str):
    """
    获取 SBOM × 指纹比对报告
    
    Request:
        - sbom_id: SBOM ID
    
    Response:
        {
            "matched": [...],
            "sbom_only": [...],
            "fingerprint_only": [...],
            "warnings": [...],
            "summary": {...}
        }
    """
    if not SBOM_AVAILABLE:
        raise HTTPException(status_code=503, detail="SBOM 模块不可用")
    
    sbom_data = sbom_db.get(sbom_id)
    
    if not sbom_data:
        raise HTTPException(status_code=404, detail="SBOM 不存在")
    
    # 获取扫描任务（如果需要）
    task_id = sbom_data.get('task_id')
    scan_result = None
    
    if task_id:
        try:
            queue = get_scan_queue()
            task = queue.get_task(task_id)
            if task and task.result:
                scan_result = task.result
        except Exception as e:
            logger.warning(f"获取扫描任务失败：{task_id}, {e}")
    
    # 比对
    try:
        components = [SBOMComponent(**comp) for comp in sbom_data['components']]
        comparison = compare_sbom_with_fingerprint(components, scan_result)
        
        return {
            "success": True,
            "comparison": comparison
        }
    except Exception as e:
        logger.error(f"比对失败：{e}")
        raise HTTPException(status_code=500, detail=f"比对失败：{str(e)}")


@sbom_router.delete("/{sbom_id}")
async def delete_sbom(sbom_id: str):
    """删除 SBOM 记录"""
    if not SBOM_AVAILABLE:
        raise HTTPException(status_code=503, detail="SBOM 模块不可用")
    
    sbom_data = sbom_db.get(sbom_id)
    
    if not sbom_data:
        raise HTTPException(status_code=404, detail="SBOM 不存在")
    
    # 删除文件
    file_path = Path(sbom_data.get('file_path', ''))
    if file_path.exists():
        file_path.unlink()
        logger.info(f"删除 SBOM 文件：{file_path}")
    
    # 删除数据库记录
    sbom_db.delete(sbom_id)
    logger.info(f"删除 SBOM 记录：{sbom_id}")
    
    return {
        "success": True,
        "message": "SBOM 已删除"
    }


@sbom_router.get("/")
async def list_sboms(limit: int = 100):
    """列出所有 SBOM 记录"""
    if not SBOM_AVAILABLE:
        raise HTTPException(status_code=503, detail="SBOM 模块不可用")
    
    sboms = sbom_db.list_all(limit)
    
    return {
        "success": True,
        "count": len(sboms),
        "sboms": sboms
    }


def register_sbom_api(app):
    """注册 SBOM API 到 FastAPI 应用"""
    app.include_router(sbom_router)
    logger.info("✅ SBOM API 已注册")
