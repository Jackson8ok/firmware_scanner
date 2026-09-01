"""
SBOM API - v2.7.0-Phase2

提供 REST API 端点用于 SBOM 导入、比对和报告

端点:
    POST   /api/sbom/import             - 导入 SBOM 文件
    GET    /api/sbom/{sbom_id}          - 获取 SBOM 详情
    GET    /api/sbom/{sbom_id}/comparison - SBOM × 指纹比对报告
    DELETE /api/sbom/{sbom_id}          - 删除 SBOM
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

try:
    from services.sbom.sbom_parser import SBOMParser, SBOMComponent, compare_sbom_with_fingerprint
    from scanner.task_queue import get_scan_queue
    SBOM_AVAILABLE = True
except ImportError as e:
    SBOM_AVAILABLE = False
    print(f"⚠️ SBOM 模块未加载：{e}")

# 创建 FastAPI Router
sbom_router = APIRouter(prefix="/api/sbom", tags=["sbom"])

# 全局存储（生产环境应使用数据库）
_sbom_store: Dict[str, Dict] = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_sbom_parser() -> SBOMParser:
    """获取 SBOM 解析器单例"""
    return SBOMParser()


@sbom_router.post("/import")
async def import_sbom(
    file: UploadFile = File(..., description="SBOM 文件 (SPDX/CycloneDX JSON/CSV)"),
    firmware_id: Optional[str] = Form(None, description="关联的固件 ID")
):
    """
    导入 SBOM 文件
    
    Request:
        - file: SBOM 文件
        - firmware_id: 可选，关联的固件扫描任务 ID
    
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
    
    # 保存文件
    upload_dir = Path("/mnt/workspace/firmware_scanner/uploads/sbom")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    # 存储
    sbom_id = f"sbom_{uuid.uuid4().hex[:12]}"
    _sbom_store[sbom_id] = {
        "sbom_id": sbom_id,
        "file_path": str(file_path),
        "firmware_id": firmware_id,
        "components": [comp.to_dict() for comp in components],
        "components_count": len(components),
        "format": parser._detect_format(file_path),
        "created_at": datetime.now().isoformat(),
        "status": "parsed"
    }
    
    logger.info(f"SBOM 导入成功：{sbom_id}, {len(components)} 个组件")
    
    return {
        "success": True,
        "sbom_id": sbom_id,
        "components_count": len(components),
        "format": _sbom_store[sbom_id]["format"],
        "status": "parsed"
    }


@sbom_router.get("/{sbom_id}")
async def get_sbom(sbom_id: str):
    """获取 SBOM 详情"""
    if not SBOM_AVAILABLE:
        raise HTTPException(status_code=503, detail="SBOM 模块不可用")
    
    if sbom_id not in _sbom_store:
        raise HTTPException(status_code=404, detail="SBOM 不存在")
    
    sbom_data = _sbom_store[sbom_id]
    
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
    
    if sbom_id not in _sbom_store:
        raise HTTPException(status_code=404, detail="SBOM 不存在")
    
    sbom_data = _sbom_store[sbom_id]
    firmware_id = sbom_data.get("firmware_id")
    
    if not firmware_id:
        raise HTTPException(status_code=400, detail="SBOM 未关联固件 ID")
    
    # 获取指纹识别结果
    try:
        queue = get_scan_queue()
        task = queue.get_task_status(firmware_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="固件扫描任务不存在")
        
        if not task.result:
            raise HTTPException(status_code=400, detail="固件扫描未完成")
        
        fingerprint_components = task.result.get("components", [])
        
    except Exception as e:
        logger.error(f"获取指纹结果失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取指纹结果失败：{str(e)}")
    
    # 比对
    sbom_components = [SBOMComponent(**comp) for comp in sbom_data["components"]]
    comparison_result = compare_sbom_with_fingerprint(sbom_components, fingerprint_components)
    
    return {
        "success": True,
        "sbom_id": sbom_id,
        "firmware_id": firmware_id,
        "comparison": comparison_result
    }


@sbom_router.delete("/{sbom_id}")
async def delete_sbom(sbom_id: str):
    """删除 SBOM"""
    if not SBOM_AVAILABLE:
        raise HTTPException(status_code=503, detail="SBOM 模块不可用")
    
    if sbom_id not in _sbom_store:
        raise HTTPException(status_code=404, detail="SBOM 不存在")
    
    # 删除文件
    sbom_data = _sbom_store[sbom_id]
    file_path = Path(sbom_data["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # 删除存储
    del _sbom_store[sbom_id]
    
    logger.info(f"SBOM 已删除：{sbom_id}")
    
    return {
        "success": True,
        "message": "SBOM 已删除"
    }


@sbom_router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "sbom_available": SBOM_AVAILABLE,
        "version": "v2.7.0-Phase2"
    }


# 注册函数
def register_sbom_api(app):
    """将 SBOM API 注册到 FastAPI 应用"""
    app.include_router(sbom_router)
    print("✅ SBOM API 已注册：/api/sbom/*")
