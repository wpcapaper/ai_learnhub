"""
知识库管理 API 路由

按照 RAG_ARCHITECTURE.md 规范设计：
- 课程级 Collection：course_{code}_{kb_version}
- Metadata 字段：code, source_file, position, char_start, char_end, content_type, char_count, estimated_tokens, kb_version
- API 使用 code（课程目录名）作为主标识符
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import time
import logging

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.admin_security import validate_chapter_name
from app.models import Chapter, ChapterKBConfig
from app.rag.service import RAGService, get_collection_name
from app.rag.vector_store import ChromaVectorStore
from app.tasks import enqueue_task, get_job_status, index_course

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/kb", tags=["知识库管理"])


# ==================== 请求/响应模型 ====================

class RAGStatusResponse(BaseModel):
    """RAG系统状态响应"""
    embedding: Dict[str, Any]
    rerank: Dict[str, Any]
    ready: bool


class KBConfigUpdate(BaseModel):
    """知识库配置更新请求"""
    chunking_strategy: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    min_chunk_size: Optional[int] = None
    code_block_strategy: Optional[str] = None
    code_summary_threshold: Optional[int] = None
    retrieval_mode: Optional[str] = None
    default_top_k: Optional[int] = None
    score_threshold: Optional[float] = None
    enable_graph_extraction: Optional[bool] = None
    graph_entity_types: Optional[List[str]] = None
    graph_relation_types: Optional[List[str]] = None


class KBConfigResponse(BaseModel):
    """知识库配置响应"""
    config: Dict[str, Any]
    stats: Dict[str, Any]


class ChunkListResponse(BaseModel):
    """文档块列表响应"""
    chunks: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class ChunkDetailResponse(BaseModel):
    """文档块详情响应"""
    id: str
    content: str
    content_type: str
    source_file: Optional[str] = None
    char_count: int
    metadata: Dict[str, Any]


class ReindexRequest(BaseModel):
    """重建索引请求"""
    clear_existing: bool = False
    kb_version: Optional[int] = None


class ReindexResponse(BaseModel):
    """重建索引响应"""
    task_id: str
    status: str
    message: str


class RetrievalTestRequest(BaseModel):
    """召回测试请求"""
    query: str
    top_k: Optional[int] = None
    retrieval_mode: Optional[str] = None
    score_threshold: Optional[float] = None


class RetrievalTestResponse(BaseModel):
    """召回测试响应"""
    results: List[Dict[str, Any]]
    query_time_ms: float


# ==================== 辅助函数 ====================

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_embedding_status() -> Dict[str, Any]:
    """检查Embedding服务状态"""
    status = {
        "available": False,
        "provider": None,
        "model": None,
        "message": None
    }
    
    try:
        rag_service = RAGService.get_instance()
        config = rag_service._config.get("embedding", {})
        provider = config.get("provider", "unknown")
        
        # 尝试编码一个简单文本验证服务可用
        rag_service.embedding_model.encode(["test"])
        
        status["available"] = True
        status["provider"] = provider
        status["model"] = config.get(provider, {}).get("model", "unknown")
        status["message"] = "Embedding 模型已就绪"
    except Exception as e:
        status["message"] = f"Embedding 不可用: {str(e)}"
    
    return status


async def check_rerank_status() -> Dict[str, Any]:
    """检查Rerank服务状态"""
    status = {
        "available": False,
        "provider": None,
        "model": None,
        "message": None
    }
    
    try:
        rag_service = RAGService.get_instance()
        rerank_config = rag_service._config.get("rerank", {})
        
        if rag_service.reranker is not None:
            status["available"] = True
            status["provider"] = rerank_config.get("provider", "unknown")
            status["model"] = rerank_config.get(rerank_config.get("provider", "local"), {}).get("model", "unknown")
            status["message"] = "Rerank 模型已就绪"
        else:
            status["message"] = "Rerank 未配置"
    except Exception as e:
        status["message"] = f"Rerank 不可用: {str(e)}"
    
    return status


def get_or_create_kb_config(
    db: Session,
    code: str,
    source_file: Optional[str] = None
) -> ChapterKBConfig:
    """获取或创建章节知识库配置"""
    temp_ref = f"{code}/{source_file}" if source_file else code
    
    config = db.query(ChapterKBConfig).filter(
        ChapterKBConfig.temp_ref == temp_ref
    ).first()
    
    if not config:
        config = ChapterKBConfig(
            id=str(uuid.uuid4()),
            course_id=None,
            chapter_id=None,
            temp_ref=temp_ref,
            created_at=datetime.utcnow()
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return config


def resolve_source_file(
    code: str,
    source_file: Optional[str],
    chapter_name: Optional[str],
    chapter_order: Optional[int]
) -> str:
    course_data = load_course_json(code)

    if chapter_order is not None:
        target_order = normalize_chapter_order(chapter_order)
        chapters = course_data.get("chapters", [])
        for chapter in chapters:
            chapter_order_value = normalize_chapter_order(
                chapter.get("sort_order", chapter.get("order"))
            )
            if chapter_order_value == target_order:
                file_name = chapter.get("file", "")
                if file_name:
                    return file_name
        if target_order is not None and chapters:
            index = target_order - 1
            if 0 <= index < len(chapters):
                file_name = chapters[index].get("file", "")
                if file_name:
                    return file_name
        raise HTTPException(status_code=404, detail="章节序号不存在")

    if source_file:
        if ".." in source_file or "/" in source_file or "\\" in source_file:
            raise HTTPException(status_code=400, detail="章节文件名包含非法字符")
        return source_file

    if not chapter_name:
        raise HTTPException(status_code=422, detail="缺少章节参数")

    if chapter_name.endswith(".md"):
        return chapter_name

    safe_name = validate_chapter_name(chapter_name)
    for chapter in course_data.get("chapters", []):
        file_name = chapter.get("file", "")
        if Path(file_name).stem == safe_name:
            return file_name

    raise HTTPException(status_code=404, detail="章节文件不存在")


def load_course_json(code: str) -> Dict[str, Any]:
    """加载课程的 course.json"""
    from app.core.paths import get_course_json_path

    course_json_path = get_course_json_path(code)
    if course_json_path.exists():
        with open(course_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def normalize_chapter_order(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_course_json(code: str, data: Dict[str, Any]) -> None:
    """保存 course.json"""
    from app.core.paths import MARKDOWN_COURSES_DIR as courses_dir
    course_json_path = courses_dir / code / "course.json"
    
    with open(course_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_current_kb_version(code: str) -> int:
    """获取当前知识库版本号"""
    course_data = load_course_json(code)
    return course_data.get("kb_version", 1)


def increment_kb_version(code: str) -> int:
    """递增知识库版本号并返回新版本"""
    course_data = load_course_json(code)
    current_version = course_data.get("kb_version", 0)
    new_version = current_version + 1
    course_data["kb_version"] = new_version
    course_data["kb_updated_at"] = datetime.utcnow().isoformat()
    save_course_json(code, course_data)
    return new_version


import uuid


# ==================== 系统状态 API ====================

@router.get("/status", response_model=RAGStatusResponse)
async def get_rag_status():
    """
    获取 RAG 系统状态
    
    检测 Embedding 和 Rerank 模型是否可用
    """
    embedding_status = await check_embedding_status()
    rerank_status = await check_rerank_status()
    
    return RAGStatusResponse(
        embedding=embedding_status,
        rerank=rerank_status,
        ready=embedding_status["available"]
    )


# ==================== 课程级 API ====================

@router.get("/courses/{code}/chunks", response_model=ChunkListResponse)
async def list_course_chunks(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_file: Optional[str] = None,
    chapter_name: Optional[str] = None,
    chapter_order: Optional[int] = Query(None, description="章节序号"),
    content_type: Optional[str] = None,
    search: Optional[str] = None,
    kb_version: Optional[int] = None
):
    """
    获取课程的文档块列表
    
    Args:
        code: 课程代码（目录名）
        source_file: 章节文件名（可选，用于按章节过滤）
        kb_version: 知识库版本（默认使用当前版本）
    """
    actual_version = kb_version or get_current_kb_version(code)
    
    try:
        rag_service = RAGService.get_instance()
        all_chunks = rag_service.get_all_chunks(code, actual_version)
        
        filter_source_file = None
        if source_file or chapter_name or chapter_order is not None:
            filter_source_file = resolve_source_file(code, source_file, chapter_name, chapter_order)

        # 过滤
        filtered_chunks = []
        for chunk in all_chunks:
            metadata = chunk.get("metadata", {})
            
            # 按章节过滤
            if filter_source_file and metadata.get("source_file") != filter_source_file:
                continue
            
            if content_type and metadata.get("content_type") != content_type:
                continue
            
            if search and search.lower() not in chunk.get("content", "").lower():
                continue
            
            filtered_chunks.append({
                "id": chunk.get("id"),
                "content": (chunk.get("content") or "")[:200] + "..." if len(chunk.get("content") or "") > 200 else chunk.get("content"),
                "content_type": metadata.get("content_type", "paragraph"),
                "source_file": metadata.get("source_file"),
                "char_count": metadata.get("char_count", len(chunk.get("content") or "")),
                "estimated_tokens": metadata.get("estimated_tokens", 0),
                "position": metadata.get("position", 0),
            })
        
        total = len(filtered_chunks)
        offset = (page - 1) * page_size
        paginated_chunks = filtered_chunks[offset:offset + page_size]
        
        return ChunkListResponse(
            chunks=paginated_chunks,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取课程文档块失败: {e}")
        return ChunkListResponse(
            chunks=[],
            total=0,
            page=page,
            page_size=page_size
        )


@router.get("/chunks/{chunk_id}", response_model=ChunkDetailResponse)
async def get_chunk_detail(
    chunk_id: str,
    code: str = Query(..., description="课程代码"),
    kb_version: Optional[int] = None
):
    """获取单个文档块详情"""
    actual_version = kb_version or get_current_kb_version(code)
    
    try:
        rag_service = RAGService.get_instance()
        vector_store = rag_service._get_vector_store(code, actual_version)
        
        chunk_data = vector_store.get_chunk_by_id(chunk_id)
        
        if not chunk_data:
            raise HTTPException(status_code=404, detail="文档块不存在")
        
        metadata = chunk_data.get("metadata", {})
        
        return ChunkDetailResponse(
            id=chunk_id,
            content=chunk_data.get("text", ""),
            content_type=metadata.get("content_type", "paragraph"),
            source_file=metadata.get("source_file"),
            char_count=len(chunk_data.get("text", "")),
            metadata=metadata
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档块失败: {str(e)}")


@router.post("/courses/reindex", response_model=ReindexResponse)
async def reindex_course(
    code: str = Query(..., description="课程代码"),
    clear_existing: bool = Query(False, description="是否清理旧索引"),
    kb_version: Optional[int] = Query(None, description="知识库版本"),
    chapters: Optional[List[Dict[str, str]]] = Body(None, description="章节列表（可选）"),
    db: Session = Depends(get_db)
):
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用")

    if not chapters:
        course_data = load_course_json(code)
        chapters = [
            {"file": ch.get("file", "")}
            for ch in course_data.get("chapters", [])
            if ch.get("file")
        ]
        if not chapters:
            raise HTTPException(status_code=404, detail="课程章节为空，无法索引")
    
    # 确定版本号
    if kb_version:
        new_version = kb_version
    elif clear_existing:
        new_version = 1
    else:
        new_version = increment_kb_version(code)
    
    # 更新章节配置状态
    for ch in chapters:
        temp_ref = f"{code}/{ch['file']}"
        config = get_or_create_kb_config(db, code, ch["file"])
        config.index_status = "pending"
        config.index_error = None
        db.commit()
    
    # 构建任务参数
    chapter_list = [
        {
            "temp_ref": f"{code}/{ch['file']}",
            "chapter_file": ch["file"]
        }
        for ch in chapters
    ]
    
    job_config = {
        "clear_existing": clear_existing,
        "kb_version": new_version
    }
    
    try:
        job_id = enqueue_task(
            index_course,
            code,
            chapter_list,
            job_config,
            queue_name="indexing",
            timeout=3600
        )
        
        # 更新任务ID
        for ch in chapter_list:
            config = get_or_create_kb_config(db, code, ch["chapter_file"])
            config.current_task_id = job_id
        db.commit()
        
        return ReindexResponse(
            task_id=job_id,
            status="queued",
            message=f"已将 {len(chapters)} 个章节加入索引队列，版本 {new_version}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务入队失败: {str(e)}")


@router.post("/chapters/reindex", response_model=ReindexResponse)
async def reindex_chapter(
    code: str = Query(..., description="课程代码"),
    source_file: Optional[str] = Query(None, description="章节文件名"),
    chapter_name: Optional[str] = Query(None, description="章节名称"),
    chapter_order: Optional[int] = Query(None, description="章节序号"),
    request: ReindexRequest = ReindexRequest(),
    db: Session = Depends(get_db)
):
    """
    重建单个章节的索引
    """
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用")
    
    actual_source_file = resolve_source_file(code, source_file, chapter_name, chapter_order)
    temp_ref = f"{code}/{actual_source_file}"
    config = get_or_create_kb_config(db, code, actual_source_file)
    config.index_status = "pending"
    config.index_error = None
    db.commit()
    
    # 确定版本号
    new_version = request.kb_version or get_current_kb_version(code)
    
    job_config = {
        "clear_existing": False,  # 单章节不清除整个 collection
        "kb_version": new_version
    }
    
    try:
        from app.tasks import index_chapter
        job_id = enqueue_task(
            index_chapter,
            temp_ref,
            code,
            actual_source_file,
            job_config,
            queue_name="indexing",
            timeout=600
        )
        
        config.current_task_id = job_id
        db.commit()
        
        return ReindexResponse(
            task_id=job_id,
            status="queued",
            message=f"章节索引任务已加入队列"
        )
    except Exception as e:
        config.index_status = "failed"
        config.index_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"任务入队失败: {str(e)}")


@router.get("/courses/{code}/pending-tasks")
async def get_course_pending_tasks(
    code: str,
    db: Session = Depends(get_db)
):
    """获取课程下所有进行中的索引任务"""
    configs = db.query(ChapterKBConfig).filter(
        ChapterKBConfig.temp_ref.like(f"{code}/%"),
        ChapterKBConfig.index_status.in_(["pending", "indexing"]),
        ChapterKBConfig.current_task_id.isnot(None)
    ).all()
    
    tasks = []
    for config in configs:
        task_info = {
            "task_id": config.current_task_id,
            "temp_ref": config.temp_ref,
            "chapter_file": config.temp_ref.split("/", 1)[1] if "/" in config.temp_ref else config.temp_ref,
            "status": config.index_status,
            "error": None
        }
        
        if config.current_task_id:
            job_status = get_job_status(config.current_task_id)
            if job_status:
                task_info["status"] = job_status.get("status", config.index_status)
                task_info["error"] = job_status.get("error")
        
        tasks.append(task_info)
    
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    status = get_job_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    return status


@router.post("/chapters/test-retrieval", response_model=RetrievalTestResponse)
async def test_retrieval(
    request: RetrievalTestRequest,
    code: str = Query(..., description="课程代码"),
    source_file: Optional[str] = Query(None, description="章节文件路径"),
    chapter_name: Optional[str] = Query(None, description="章节名称"),
    chapter_order: Optional[int] = Query(None, description="章节序号"),
    kb_version: Optional[int] = Query(None, description="知识库版本")
):
    """召回测试"""
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用")
    
    actual_version = kb_version or get_current_kb_version(code)
    
    start_time = time.time()
    
    rag_service = RAGService.get_instance()
    
    # 构建过滤器
    filters = None
    if source_file or chapter_name or chapter_order is not None:
        actual_source_file = resolve_source_file(code, source_file, chapter_name, chapter_order)
        filters = {"source_file": actual_source_file}
    
    top_k = request.top_k or 5
    score_threshold = request.score_threshold or 0.0
    
    results = await rag_service.retrieve(
        query=request.query,
        code=code,
        kb_version=actual_version,
        top_k=top_k,
        filters=filters,
        score_threshold=score_threshold
    )
    
    query_time_ms = (time.time() - start_time) * 1000
    
    formatted_results = []
    for r in results:
        text = r.text or ""
        formatted_results.append({
            "chunk_id": r.chunk_id,
            "content": text[:500] + "..." if len(text) > 500 else text,
            "score": r.score,
            "source": r.metadata.get("source_file", "未知来源")
        })
    
    return RetrievalTestResponse(
        results=formatted_results,
        query_time_ms=query_time_ms
    )


# ==================== 配置管理 API ====================

@router.get("/chapters/config")
async def get_chapter_kb_config(
    code: str,
    source_file: Optional[str] = Query(None, description="章节文件名"),
    chapter_name: Optional[str] = Query(None, description="章节名称"),
    chapter_order: Optional[int] = Query(None, description="章节序号"),
    db: Session = Depends(get_db)
):
    """获取章节知识库配置"""
    actual_source_file = resolve_source_file(code, source_file, chapter_name, chapter_order)
    config = get_or_create_kb_config(db, code, actual_source_file)
    
    return KBConfigResponse(
        config=config.to_dict(),
        stats={
            "chunk_count": config.chunk_count,
            "graph_entity_count": config.graph_entity_count,
            "graph_relation_count": config.graph_relation_count,
            "index_status": config.index_status,
            "indexed_at": config.indexed_at.isoformat() if config.indexed_at else None,
            "metadata_backfilled": config.metadata_backfilled
        }
    )


@router.put("/chapters/config")
async def update_chapter_kb_config(
    code: str,
    update: KBConfigUpdate,
    source_file: Optional[str] = Query(None, description="章节文件名"),
    chapter_name: Optional[str] = Query(None, description="章节名称"),
    chapter_order: Optional[int] = Query(None, description="章节序号"),
    db: Session = Depends(get_db)
):
    """更新章节知识库配置"""
    actual_source_file = resolve_source_file(code, source_file, chapter_name, chapter_order)
    config = get_or_create_kb_config(db, code, actual_source_file)
    
    update_fields = {
        'chunking_strategy': update.chunking_strategy,
        'chunk_size': update.chunk_size,
        'chunk_overlap': update.chunk_overlap,
        'min_chunk_size': update.min_chunk_size,
        'code_block_strategy': update.code_block_strategy,
        'code_summary_threshold': update.code_summary_threshold,
        'retrieval_mode': update.retrieval_mode,
        'default_top_k': update.default_top_k,
        'score_threshold': update.score_threshold,
        'enable_graph_extraction': update.enable_graph_extraction,
        'graph_entity_types': update.graph_entity_types,
        'graph_relation_types': update.graph_relation_types,
    }
    
    for field, value in update_fields.items():
        if value is not None:
            setattr(config, field, value)
    
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    
    return {"message": "配置已更新", "config": config.to_dict()}


# ==================== 课程信息 API ====================

@router.get("/courses")
async def list_kb_courses():
    """列出所有可用于知识库管理的课程"""
    from app.core.paths import MARKDOWN_COURSES_DIR as courses_dir
    
    if not courses_dir.exists():
        return {"courses": []}
    
    courses = []
    for course_dir in courses_dir.iterdir():
        if course_dir.is_dir():
            course_json = course_dir / "course.json"
            if course_json.exists():
                with open(course_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    courses.append({
                        "code": data.get("code", course_dir.name),
                        "title": data.get("title", course_dir.name),
                        "kb_version": data.get("kb_version", 1),
                        "chapters": data.get("chapters", [])
                    })
    
    return {"courses": courses}
