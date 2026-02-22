"""
知识库管理 API 路由

提供章节级别的知识库管理功能：
- 系统状态检测（Embedding/Rerank 是否可用）
- 章节知识库配置管理
- 文档块管理（通过 ChromaDB）
- 召回测试

架构说明：
- 业务数据库：只存储 ChapterKBConfig（配置需要关联 course_id/chapter_id）
- ChromaDB：存储所有 RAG 数据（向量 + 元数据），完全独立
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import uuid
import time
import logging

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import Chapter, ChapterKBConfig
from app.rag.service import RAGService, normalize_collection_name
from app.rag.vector_store import ChromaVectorStore
from app.tasks import enqueue_task, get_job_status, index_chapter, index_course

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
    """文档块列表响应（从 ChromaDB 获取）"""
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
    is_active: bool
    metadata: Dict[str, Any]


class ReindexRequest(BaseModel):
    """重建索引请求"""
    clear_existing: bool = False


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


class MetadataBackfillRequest(BaseModel):
    """元数据回填请求"""
    course_id: str
    chapters: List[Dict[str, str]]


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
    chapter_id: str = None, 
    course_id: str = None,
    temp_ref: str = None
) -> ChapterKBConfig:
    """获取或创建章节知识库配置"""
    config = None
    
    if chapter_id:
        config = db.query(ChapterKBConfig).filter(
            ChapterKBConfig.chapter_id == chapter_id
        ).first()
    elif temp_ref:
        config = db.query(ChapterKBConfig).filter(
            ChapterKBConfig.temp_ref == temp_ref
        ).first()
    
    if not config:
        config = ChapterKBConfig(
            id=str(uuid.uuid4()),
            chapter_id=chapter_id,
            course_id=course_id,
            temp_ref=temp_ref,
            created_at=datetime.utcnow()
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return config


def get_chapter_collection_name(chapter_id: str) -> str:
    """获取章节对应的 ChromaDB collection 名称"""
    return f"chapter_{chapter_id}"


def get_chroma_store(chapter_id: str) -> ChromaVectorStore:
    """获取章节对应的 ChromaDB 存储"""
    rag_service = RAGService.get_instance()
    collection_name = get_chapter_collection_name(chapter_id)
    return ChromaVectorStore(
        collection_name=collection_name,
        persist_directory=rag_service.persist_directory
    )


# ==================== 系统状态 API ====================

@router.get("/status", response_model=RAGStatusResponse)
async def get_rag_status():
    """
    获取 RAG 系统状态
    
    检测 Embedding 和 Rerank 模型是否可用
    前端应根据此状态决定是否启用 RAG 功能
    """
    embedding_status = await check_embedding_status()
    rerank_status = await check_rerank_status()
    
    return RAGStatusResponse(
        embedding=embedding_status,
        rerank=rerank_status,
        ready=embedding_status["available"]
    )


# ==================== 章节知识库配置 API ====================

@router.get("/chapters/config")
async def get_chapter_kb_config_by_ref(
    temp_ref: str,
    db: Session = Depends(get_db)
):
    config = get_or_create_kb_config(db, temp_ref=temp_ref)
    
    chunk_count = 0
    try:
        # 从 temp_ref 提取 course_code 和 chapter_file
        course_code = temp_ref.split("/")[0] if "/" in temp_ref else temp_ref
        chapter_file = temp_ref.split("/")[1] if "/" in temp_ref else None
        
        # 本地数据源使用 course_local_{course_code}
        rag_service = RAGService.get_instance()
        store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_local_{course_code}"),
            persist_directory=rag_service.persist_directory
        )
        
        # 按 source_file 过滤计数
        all_chunks = store.get_all_chunks()
        chunk_count = sum(
            1 for chunk in all_chunks 
            if chapter_file and chapter_file in chunk.get("metadata", {}).get("source_file", "")
        )
    except Exception:
        pass
    
    return KBConfigResponse(
        config=config.to_dict(),
        stats={
            "chunk_count": chunk_count,
            "graph_entity_count": config.graph_entity_count,
            "graph_relation_count": config.graph_relation_count,
            "index_status": config.index_status,
            "indexed_at": config.indexed_at.isoformat() if config.indexed_at else None,
            "metadata_backfilled": config.metadata_backfilled
        }
    )


@router.put("/chapters/config")
async def update_chapter_kb_config_by_ref(
    temp_ref: str,
    update: KBConfigUpdate,
    db: Session = Depends(get_db)
):
    config = get_or_create_kb_config(db, temp_ref=temp_ref)
    
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


@router.post("/chapters/reindex", response_model=ReindexResponse)
async def reindex_chapter_by_ref(
    temp_ref: str,
    request: ReindexRequest,
    db: Session = Depends(get_db)
):
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用，无法重建索引")
    
    config = get_or_create_kb_config(db, temp_ref=temp_ref)
    config.index_status = "pending"
    config.index_error = None
    db.commit()
    
    course_dir = temp_ref.split("/")[0]
    chapter_file = "/".join(temp_ref.split("/")[1:])
    
    job_config = {
        "chunking_strategy": config.chunking_strategy,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
        "min_chunk_size": config.min_chunk_size,
        "code_block_strategy": config.code_block_strategy,
        "clear_existing": request.clear_existing
    }
    
    try:
        job_id = enqueue_task(
            index_chapter,
            temp_ref,
            course_dir,
            chapter_file,
            job_config,
            queue_name="indexing",
            timeout=600
        )
        
        if job_id:
            config.current_task_id = job_id
            db.commit()
        
        return ReindexResponse(
            task_id=job_id or temp_ref,
            status="queued",
            message="索引任务已加入队列"
        )
    except Exception as e:
        config.index_status = "failed"
        config.index_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"任务入队失败: {str(e)}")


@router.post("/chapters/sync-to-db")
async def sync_chunks_to_db(
    temp_ref: str = Query(..., description="本地文件引用（格式：course_id/chapter_file）"),
    chapter_id: str = Query(..., description="数据库章节ID（UUID）"),
    db: Session = Depends(get_db)
):
    """
    将本地分块同步为线上课程分块（幂等操作）
    
    本地分块：metadata.chapter_id = temp_ref（如 python_basics/01_introduction.md）
    线上分块：metadata.chapter_id = UUID（如 00d7be63-5c87-43ab-ac36-7a7e45f46c7b）
    
    幂等性保证：
    1. 使用固定格式的 chunk_id（sync_{chapter_id_hash}_{position}）
    2. 先创建新分块，成功后删除旧的线上分块
    
    版本控制：
    1. 同步后的分块保留 strategy_version 和 indexed_at
    2. 新增 synced_from 字段记录来源 temp_ref
    """
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用")
    
    # 验证数据库章节存在
    from app.models import Chapter
    db_chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not db_chapter:
        raise HTTPException(status_code=404, detail="数据库章节不存在")
    
    try:
        from app.rag.service import RAGService
        from app.rag.vector_store import ChromaVectorStore
        import hashlib
        from datetime import datetime, timezone
        from app.rag.chunking.version import CURRENT_STRATEGY_VERSION
        
        rag_service = RAGService.get_instance()
        
        course_code = temp_ref.split("/")[0]
        
        # 本地数据源
        local_store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_local_{course_code}"),
            persist_directory=rag_service.persist_directory
        )
        
        # 线上数据源
        online_store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_online_{course_code}"),
            persist_directory=rag_service.persist_directory
        )
        
        # 步骤1：从本地数据源获取分块
        all_chunks = local_store.get_all_chunks()
        local_chunk_ids = [
            chunk["id"] for chunk in all_chunks
            if chunk.get("metadata", {}).get("chapter_id") == temp_ref
        ]
        
        if not local_chunk_ids:
            return {
                "success": True,
                "chapter_id": chapter_id,
                "temp_ref": temp_ref,
                "chunk_count": 0,
                "message": "没有找到本地分块数据"
            }
        
        # 获取本地分块及其 embeddings
        local_chunks = local_store.get_chunks_with_embeddings(local_chunk_ids)
        
        # 按 position 排序
        local_chunks.sort(key=lambda x: x.get("metadata", {}).get("position", 0))
        
        # 步骤2：生成幂等的 chunk_id 并准备新分块
        chapter_id_hash = hashlib.md5(chapter_id.encode()).hexdigest()[:12]
        new_chunks_data = []
        new_embeddings = []
        now_iso = datetime.now(timezone.utc).isoformat()
        
        for i, chunk in enumerate(local_chunks):
            emb = chunk.get("embedding")
            if emb is None:
                continue
            
            new_chunk_id = f"sync_{chapter_id_hash}_{i:04d}"
            old_metadata = chunk.get("metadata", {})
            
            new_metadata = {
                **old_metadata,
                "chapter_id": chapter_id,
                "course_id": db_chapter.course_id,
                "synced_from": temp_ref,
                "synced_at": now_iso,
                "strategy_version": CURRENT_STRATEGY_VERSION,
            }
            
            new_chunks_data.append({
                "id": new_chunk_id,
                "text": chunk.get("content", ""),
                "metadata": new_metadata
            })
            
            if hasattr(emb, 'tolist'):
                new_embeddings.append(emb.tolist())
            else:
                new_embeddings.append(emb)
        
        # 步骤3：获取旧的线上分块
        online_chunks = online_store.get_all_chunks()
        old_synced_ids = [
            chunk["id"] for chunk in online_chunks
            if chunk.get("metadata", {}).get("chapter_id") == chapter_id
            and chunk["id"].startswith(f"sync_{chapter_id_hash}_")
        ]
        
        # 步骤4：写入新分块到线上数据源
        if new_chunks_data and new_embeddings:
            online_store.add_chunks(new_chunks_data, new_embeddings)
        
        
        
        # 步骤5：删除旧的线上分块
        if old_synced_ids:
            online_store.delete_chunks(old_synced_ids)
        
        chunk_count = len(new_chunks_data)
        
        return {
            "success": True,
            "chapter_id": chapter_id,
            "temp_ref": temp_ref,
            "chunk_count": chunk_count,
            "old_chunks_removed": len(old_synced_ids),
            "message": f"已同步 {chunk_count} 个分块到线上课程"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/courses/{course_code}/sync-all")
async def sync_course_to_online(
    course_code: str,
    db: Session = Depends(get_db)
):
    """
    一键同步课程所有章节到线上
    
    将课程下所有已索引的本地分块同步为线上课程分块
    """
    from app.models import Course, Chapter
    from pathlib import Path
    
    course = db.query(Course).filter(Course.code == course_code).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    try:
        from app.rag.service import RAGService
        from app.rag.vector_store import ChromaVectorStore
        import hashlib
        from datetime import datetime, timezone
        from app.rag.chunking.version import CURRENT_STRATEGY_VERSION
        
        rag_service = RAGService.get_instance()
        
        # 查找课程目录（使用目录名，不是 code）
        courses_base_dir = Path(__file__).parent.parent.parent / "courses"
        course_dir = None
        for d in courses_base_dir.iterdir():
            if d.is_dir():
                course_json = d / "course.json"
                if course_json.exists():
                    import json
                    data = json.loads(course_json.read_text(encoding="utf-8"))
                    if data.get("code") == course_code:
                        course_dir = d
                        break
        
        if not course_dir:
            raise HTTPException(status_code=404, detail="找不到课程目录")
        
        # 使用目录名作为 collection 标识
        dir_name = course_dir.name
        
        # 本地数据源
        local_store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_local_{dir_name}"),
            persist_directory=rag_service.persist_directory
        )
        
        # 线上数据源
        online_store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_online_{dir_name}"),
            persist_directory=rag_service.persist_directory
        )
        
        all_chunks = local_store.get_all_chunks()
        
        course_json_path = course_dir / "course.json"
        
        local_chapters = {}
        if course_json_path.exists():
            import json
            course_data = json.loads(course_json_path.read_text(encoding="utf-8"))
            for ch in course_data.get("chapters", []):
                file = ch.get("file", "")
                title = ch.get("title", "")
                if file and title:
                    local_chapters[title] = file
        
        # 获取数据库章节
        db_chapters = db.query(Chapter).filter(Chapter.course_id == course.id).all()
        db_chapter_map = {ch.title: ch for ch in db_chapters}
        
        # 按 chapter_id（目录名格式）分组本地分块
        chapters_chunks = {}
        for chunk in all_chunks:
            meta = chunk.get("metadata", {})
            chapter_id = meta.get("chapter_id", "")
            if chapter_id and chapter_id.startswith(f"{dir_name}/"):
                chapters_chunks.setdefault(chapter_id, []).append(chunk)
        
        total_synced = 0
        total_chunks = 0
        
        for temp_ref, chunks in chapters_chunks.items():
            file_path = temp_ref[len(f"{dir_name}/"):] if temp_ref.startswith(f"{dir_name}/") else temp_ref
            
            db_chapter = None
            for title, file in local_chapters.items():
                if file == file_path:
                    db_chapter = db_chapter_map.get(title)
                    break
            
            if not db_chapter:
                continue
            
            # 获取带 embedding 的分块
            chunk_ids = [c["id"] for c in chunks]
            local_chunks = local_store.get_chunks_with_embeddings(chunk_ids)
            local_chunks.sort(key=lambda x: x.get("metadata", {}).get("position", 0))
            
            if not local_chunks:
                continue
            
            chapter_id_hash = hashlib.md5(str(db_chapter.id).encode()).hexdigest()[:12]
            new_chunks_data = []
            new_embeddings = []
            now_iso = datetime.now(timezone.utc).isoformat()
            
            for i, chunk in enumerate(local_chunks):
                emb = chunk.get("embedding")
                if emb is None:
                    continue
                
                new_chunk_id = f"sync_{chapter_id_hash}_{i:04d}"
                old_metadata = chunk.get("metadata", {})
                
                new_metadata = {
                    **old_metadata,
                    "chapter_id": str(db_chapter.id),
                    "course_id": str(course.id),
                    "synced_from": old_metadata.get("chapter_id", ""),
                    "synced_at": now_iso,
                    "strategy_version": CURRENT_STRATEGY_VERSION,
                }
                
                new_chunks_data.append({
                    "id": new_chunk_id,
                    "text": chunk.get("content", ""),
                    "metadata": new_metadata
                })
                
                if hasattr(emb, 'tolist'):
                    new_embeddings.append(emb.tolist())
                else:
                    new_embeddings.append(emb)
            
            if new_chunks_data and new_embeddings:
                online_store.add_chunks(new_chunks_data, new_embeddings)
                total_synced += 1
                total_chunks += len(new_chunks_data)
        
        return {
            "success": True,
            "course_code": course_code,
            "synced_chapters": total_synced,
            "total_chunks": total_chunks,
            "message": f"已同步 {total_synced} 个章节，共 {total_chunks} 个分块"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/courses/reindex")
async def reindex_course(
    course_id: str,
    chapters: List[Dict[str, str]],
    clear_existing: bool = False,
    force: bool = Query(False, description="强制重新执行，取消已有任务"),
    db: Session = Depends(get_db)
):
    """
    批量索引课程下所有章节
    
    Args:
        course_id: 课程 ID（目录名）
        chapters: 章节列表，格式 [{"file": "01_intro.md", "temp_ref": "..."}]
        clear_existing: 是否清除已有索引
        force: 是否强制重新执行（取消已有任务）
    """
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用")
    
    # 检查是否有正在执行的任务
    running_tasks = []
    for ch in chapters:
        temp_ref = ch.get("temp_ref") or f"{course_id}/{ch['file']}"
        config = get_or_create_kb_config(db, temp_ref=temp_ref)
        
        if config.current_task_id:
            job_status = get_job_status(config.current_task_id)
            if job_status:
                status = job_status.get("status")
                if status in ("queued", "started"):
                    running_tasks.append({
                        "temp_ref": temp_ref,
                        "task_id": config.current_task_id,
                        "status": status
                    })
    
    if running_tasks and not force:
        raise HTTPException(
            status_code=409, 
            detail={
                "message": "有任务正在执行中，请等待完成或使用 force=true 强制重新执行",
                "running_tasks": running_tasks
            }
        )
    
    # 如果强制执行，清除已有任务的 task_id
    if running_tasks and force:
        for task in running_tasks:
            config = db.query(ChapterKBConfig).filter(
                ChapterKBConfig.temp_ref == task["temp_ref"]
            ).first()
            if config:
                config.current_task_id = None
                config.index_status = "not_indexed"
        db.commit()
    
    chapter_list = []
    for ch in chapters:
        temp_ref = ch.get("temp_ref") or f"{course_id}/{ch['file']}"
        
        config = get_or_create_kb_config(db, temp_ref=temp_ref)
        config.index_status = "pending"
        config.index_error = None
        db.commit()
        
        chapter_list.append({
            "chapter_id": ch.get("chapter_id"),
            "temp_ref": temp_ref,
            "chapter_file": ch["file"]
        })
    
    try:
        job_id = enqueue_task(
            index_course,
            course_id,
            chapter_list,
            {"clear_existing": clear_existing},
            queue_name="indexing",
            timeout=3600
        )
        
        # 将任务ID存储到每个章节的配置中，用于追踪进度
        for ch in chapter_list:
            config = get_or_create_kb_config(db, temp_ref=ch["temp_ref"])
            config.current_task_id = job_id
        db.commit()
        
        return {
            "task_id": job_id,
            "status": "queued",
            "message": f"已将 {len(chapters)} 个章节加入索引队列"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务入队失败: {str(e)}")


@router.get("/courses/{course_id}/pending-tasks")
async def get_course_pending_tasks(
    course_id: str,
    db: Session = Depends(get_db)
):
    """
    获取课程下所有进行中的索引任务
    
    返回格式:
    {
        "tasks": [
            {
                "task_id": "xxx",
                "temp_ref": "course_id/chapter_file",
                "chapter_title": "章节标题",
                "status": "queued|started|finished|failed",
                "error": null
            }
        ]
    }
    """
    configs = db.query(ChapterKBConfig).filter(
        ChapterKBConfig.temp_ref.like(f"{course_id}/%"),
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


@router.get("/chapters/chunks", response_model=ChunkListResponse)
async def list_chapter_chunks_by_ref(
    temp_ref: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    content_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    course_code = temp_ref.split("/")[0] if "/" in temp_ref else temp_ref
    chapter_file = temp_ref.split("/")[1] if "/" in temp_ref else None
    
    try:
        rag_service = RAGService.get_instance()
        store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_local_{course_code}"),
            persist_directory=rag_service.persist_directory
        )
        all_chunks = store.get_all_chunks()
        
        filtered_chunks = []
        for chunk in all_chunks:
            metadata = chunk.get("metadata", {})
            
            # 按章节文件过滤（使用 source_file 字段）
            source_file = metadata.get("source_file", "")
            if chapter_file and chapter_file not in source_file:
                continue
            
            if content_type and metadata.get("content_type") != content_type:
                continue
            if search and search.lower() not in chunk.get("content", "").lower():
                continue
            
            filtered_chunks.append({
                "id": chunk.get("id"),
                "content": chunk.get("content", "")[:200] + "..." if len(chunk.get("content", "")) > 200 else chunk.get("content", ""),
                "content_type": metadata.get("content_type", "text"),
                "source_file": metadata.get("source_file"),
                "char_count": metadata.get("char_count", len(chunk.get("content", ""))),
                "estimated_tokens": metadata.get("estimated_tokens", 0),
                "token_level": metadata.get("token_level", "normal"),
                "is_active": metadata.get("is_active", True),
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
        
    except Exception:
        return ChunkListResponse(
            chunks=[],
            total=0,
            page=page,
            page_size=page_size
        )


@router.get("/chapters/{chapter_id}/chunks", response_model=ChunkListResponse)
async def list_chapter_chunks_by_id(
    chapter_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    content_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    按章节ID（UUID）查询线上课程分块
    
    线上课程分块的 metadata.chapter_id = UUID
    """
    from app.models import Chapter, Course
    from pathlib import Path
    
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    
    course = db.query(Course).filter(Course.id == chapter.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    # 查找课程目录名（用于匹配 collection）
    courses_base_dir = Path(__file__).parent.parent.parent / "courses"
    course_dir = None
    for d in courses_base_dir.iterdir():
        if d.is_dir():
            course_json = d / "course.json"
            if course_json.exists():
                import json
                data = json.loads(course_json.read_text(encoding="utf-8"))
                if data.get("code") == course.code:
                    course_dir = d
                    break
    
    if not course_dir:
        raise HTTPException(status_code=404, detail="课程目录不存在")
    
    try:
        rag_service = RAGService.get_instance()
        store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_online_{dir_name}"),
            persist_directory=rag_service.persist_directory
        )
        all_chunks = store.get_all_chunks()
        
        filtered_chunks = []
        for chunk in all_chunks:
            metadata = chunk.get("metadata", {})
            
            if metadata.get("chapter_id") != chapter_id:
                continue
            
            if content_type and metadata.get("content_type") != content_type:
                continue
            if search and search.lower() not in chunk.get("content", "").lower():
                continue
            
            filtered_chunks.append({
                "id": chunk.get("id"),
                "content": chunk.get("content", "")[:200] + "..." if len(chunk.get("content", "")) > 200 else chunk.get("content", ""),
                "content_type": metadata.get("content_type", "text"),
                "source_file": metadata.get("source_file"),
                "char_count": metadata.get("char_count", len(chunk.get("content", ""))),
                "estimated_tokens": metadata.get("estimated_tokens", 0),
                "token_level": metadata.get("token_level", "normal"),
                "is_active": metadata.get("is_active", True),
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
    
    except Exception:
        return ChunkListResponse(
            chunks=[],
            total=0,
            page=page,
            page_size=page_size
        )


@router.get("/chunks/{chunk_id}", response_model=ChunkDetailResponse)
async def get_chunk_detail(
    chunk_id: str,
    course_id: str = Query(..., description="课程ID"),
    db: Session = Depends(get_db)
):
    """获取单个文档块详情"""
    try:
        rag_service = RAGService.get_instance()
        store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_{course_id}"),
            persist_directory=rag_service.persist_directory
        )
        
        chunk_data = store.get_chunk_by_id(chunk_id)
        
        if not chunk_data:
            raise HTTPException(status_code=404, detail="文档块不存在")
        
        metadata = chunk_data.get("metadata", {})
        
        return ChunkDetailResponse(
            id=chunk_id,
            content=chunk_data.get("text", ""),
            content_type=metadata.get("content_type", "text"),
            source_file=metadata.get("source_file"),
            char_count=len(chunk_data.get("text", "")),
            is_active=metadata.get("is_active", True),
            metadata=metadata
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档块失败: {str(e)}")


@router.post("/chapters/test-retrieval", response_model=RetrievalTestResponse)
async def test_retrieval_by_ref(
    temp_ref: str,
    request: RetrievalTestRequest,
    db: Session = Depends(get_db)
):
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用")
    
    config = get_or_create_kb_config(db, temp_ref=temp_ref)
    
    if config.index_status != "indexed":
        raise HTTPException(status_code=400, detail="章节尚未建立索引")
    
    start_time = time.time()
    
    course_code = temp_ref.split("/")[0] if "/" in temp_ref else temp_ref
    
    rag_service = RAGService.get_instance()
    
    store = ChromaVectorStore(
        collection_name=normalize_collection_name(f"course_local_{course_code}"),
        persist_directory=rag_service.persist_directory
    )
    
    query_embedding = rag_service.embedding_model.encode([request.query])[0]
    
    top_k = request.top_k or config.default_top_k
    score_threshold = request.score_threshold if request.score_threshold is not None else config.score_threshold
    
    results = store.search(
        query_embedding=query_embedding,
        top_k=top_k
    )
    
    if score_threshold > 0:
        results = [r for r in results if r["score"] >= score_threshold]
    
    query_time_ms = (time.time() - start_time) * 1000
    
    formatted_results = []
    for r in results:
        text = r.get("text", "") or ""
        formatted_results.append({
            "chunk_id": r["id"],
            "content": text[:500] + "..." if len(text) > 500 else text,
            "score": r.get("score", 0),
            "source": r.get("metadata", {}).get("source_file", "未知来源")
        })
    
    return RetrievalTestResponse(
        results=formatted_results,
        query_time_ms=query_time_ms
    )


@router.get("/chapters/{chapter_id}/config", response_model=KBConfigResponse)
async def get_chapter_kb_config(
    chapter_id: str,
    db: Session = Depends(get_db)
):
    """获取章节知识库配置"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    
    config = get_or_create_kb_config(db, chapter_id=chapter_id, course_id=chapter.course_id)
    
    # 从 ChromaDB 获取实际统计
    chunk_count = 0
    try:
        store = get_chroma_store(chapter_id)
        chunk_count = store.get_collection_size()
    except Exception:
        pass
    
    return KBConfigResponse(
        config=config.to_dict(),
        stats={
            "chunk_count": chunk_count,
            "graph_entity_count": config.graph_entity_count,
            "graph_relation_count": config.graph_relation_count,
            "index_status": config.index_status,
            "indexed_at": config.indexed_at.isoformat() if config.indexed_at else None,
            "metadata_backfilled": config.metadata_backfilled
        }
    )


@router.put("/chapters/{chapter_id}/config")
async def update_chapter_kb_config(
    chapter_id: str,
    update: KBConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新章节知识库配置"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    
    config = get_or_create_kb_config(db, chapter_id=chapter_id, course_id=chapter.course_id)
    
    # 更新配置字段
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


@router.post("/chapters/{chapter_id}/reindex", response_model=ReindexResponse)
async def reindex_chapter(
    chapter_id: str,
    request: ReindexRequest,
    db: Session = Depends(get_db)
):
    """
    重建章节索引
    
    根据章节配置重新切分文档并生成向量索引
    所有数据存储在 ChromaDB，与业务数据库完全解耦
    """
    # 检查Embedding是否可用
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用，无法重建索引")
    
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    
    config = get_or_create_kb_config(db, chapter_id=chapter_id, course_id=chapter.course_id)
    
    # 更新状态为索引中
    config.index_status = "indexing"
    config.index_error = None
    db.commit()
    
    task_id = str(uuid.uuid4())[:8]
    
    try:
        # 获取章节内容
        content = chapter.content_markdown
        if not content:
            raise ValueError("章节内容为空")
        
        # 初始化RAG服务
        rag_service = RAGService.get_instance()
        
        # 根据配置调整切分策略
        if config.chunking_strategy == "semantic":
            from app.rag.chunking import SemanticChunkingStrategy
            rag_service.chunking_strategy = SemanticChunkingStrategy(
                min_chunk_size=config.min_chunk_size,
                max_chunk_size=config.chunk_size,
                overlap_size=config.chunk_overlap
            )
        
        # 清除旧索引（在 ChromaDB 中）
        if request.clear_existing:
            try:
                store = get_chroma_store(chapter_id)
                store.delete_collection()
            except Exception:
                pass
        
        # 执行索引（数据存入 ChromaDB）
        chunk_count = await rag_service.index_course_content(
            content=content,
            course_id=chapter.course_id,
            chapter_id=chapter_id,
            chapter_title=chapter.title,
            clear_existing=request.clear_existing
        )
        
        # 更新配置状态（业务数据库只存状态）
        config.index_status = "indexed"
        config.chunk_count = chunk_count
        config.indexed_at = datetime.utcnow()
        config.metadata_backfilled = True
        config.updated_at = datetime.utcnow()
        db.commit()
        
        return ReindexResponse(
            task_id=task_id,
            status="completed",
            message=f"索引完成，共 {chunk_count} 个文档块（存储在 ChromaDB）"
        )
        
    except Exception as e:
        # 记录错误
        config.index_status = "failed"
        config.index_error = str(e)
        config.updated_at = datetime.utcnow()
        db.commit()
        
        raise HTTPException(status_code=500, detail=f"索引失败: {str(e)}")





# ==================== 召回测试 API ====================

@router.post("/chapters/{chapter_id}/test-retrieval", response_model=RetrievalTestResponse)
async def test_retrieval(
    chapter_id: str,
    request: RetrievalTestRequest,
    db: Session = Depends(get_db)
):
    """召回测试"""
    # 检查Embedding是否可用
    embedding_status = await check_embedding_status()
    if not embedding_status["available"]:
        raise HTTPException(status_code=503, detail="Embedding 服务不可用")
    
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    
    config = get_or_create_kb_config(db, chapter_id=chapter_id, course_id=chapter.course_id)
    
    if config.index_status != "indexed":
        raise HTTPException(status_code=400, detail="章节尚未建立索引")
    
    start_time = time.time()
    
    # 执行检索
    rag_service = RAGService.get_instance()
    
    top_k = request.top_k or config.default_top_k
    retrieval_mode = request.retrieval_mode or config.retrieval_mode
    score_threshold = request.score_threshold if request.score_threshold is not None else config.score_threshold
    
    results = await rag_service.retrieve(
        query=request.query,
        course_id=chapter.course_id,
        top_k=top_k,
        mode=retrieval_mode,
        score_threshold=score_threshold
    )
    
    query_time_ms = (time.time() - start_time) * 1000
    
    # 格式化结果
    formatted_results = []
    for r in results:
        formatted_results.append({
            "chunk_id": r.chunk_id,
            "content": r.text[:500] + "..." if len(r.text) > 500 else r.text,
            "full_content": r.text,
            "score": r.score,
            "source": r.source
        })
    
    return RetrievalTestResponse(
        results=formatted_results,
        query_time_ms=query_time_ms
    )


# ==================== 元数据回填 API ====================

@router.post("/backfill-metadata")
async def backfill_metadata(
    request: MetadataBackfillRequest,
    db: Session = Depends(get_db)
):
    """
    批量回填元数据
    
    在课程导入时调用，将 course_id/chapter_id 回填到配置
    注意：ChromaDB 中的元数据需要单独更新（如果需要）
    """
    backfilled_count = 0
    
    for chapter_info in request.chapters:
        chapter_id = chapter_info.get("chapter_id")
        temp_ref = chapter_info.get("temp_ref")
        
        if not chapter_id or not temp_ref:
            continue
        
        # 查找待回填的配置
        configs = db.query(ChapterKBConfig).filter(
            ChapterKBConfig.temp_ref == temp_ref,
            ChapterKBConfig.metadata_backfilled.is_(False)
        ).all()
        
        for config in configs:
            config.course_id = request.course_id
            config.chapter_id = chapter_id
            config.metadata_backfilled = True
            backfilled_count += 1
    
    db.commit()
    
    return {
        "message": "元数据回填完成",
        "backfilled_count": backfilled_count,
        "note": "ChromaDB 中的向量元数据是独立的，如需更新请重建索引"
    }
