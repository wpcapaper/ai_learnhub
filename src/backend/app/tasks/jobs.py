"""
异步任务函数

定义可在后台执行的任务函数，包括：
- 词云生成
- 知识图谱生成
- Quiz 自动生成

所有任务函数都会被 Langfuse 追踪。
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.rag.service import RAGService, normalize_collection_name
from app.rag.vector_store import ChromaVectorStore
from app.core.database import SessionLocal
from app.models import ChapterKBConfig
from app.tasks.queue import acquire_course_lock, release_course_lock

logger = logging.getLogger(__name__)


def _create_trace(name: str, tags: list):
    """创建 Langfuse trace 的辅助函数"""
    from app.llm.langfuse_wrapper import _get_langfuse_client
    from datetime import datetime as dt
    
    langfuse_client = _get_langfuse_client()
    if not langfuse_client:
        return None, None, None
    
    start_time = dt.now()
    trace = langfuse_client.trace(name=name, tags=tags)
    return langfuse_client, trace, start_time


def _finish_trace(langfuse_client, trace, start_time, input_data: dict, output_data: dict, error: str = None):
    """完成 Langfuse trace 的辅助函数"""
    if not langfuse_client or not trace:
        return
    
    from datetime import datetime as dt
    end_time = dt.now()
    duration_ms = (end_time - start_time).total_seconds() * 1000
    
    if error:
        output_data["error"] = error
    
    trace_span_name = "task_call"
    if hasattr(trace, 'name'):
        trace_span_name = f"{trace.name}_call"
    
    trace.span(
        name=trace_span_name,
        input=input_data,
        output=output_data,
        start_time=start_time,
        end_time=end_time,
        metadata={"duration_ms": duration_ms},
    )
    
    trace.update(output=output_data)
    langfuse_client.flush()


def generate_wordcloud(
    chapter_id: str,
    course_id: str,
    user_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成词云
    
    基于章节内容生成词云图片。
    
    Args:
        chapter_id: 章节 ID
        course_id: 课程 ID
        user_id: 用户 ID（可选）
        config: 配置参数（可选）
            - width: 图片宽度
            - height: 图片高度
            - max_words: 最大词数
            - background_color: 背景颜色
    
    Returns:
        包含图片 URL 的字典
    """
    # 创建 trace
    langfuse_client, trace, start_time = _create_trace("generate_wordcloud", ["task", "wordcloud"])
    
    # 准备 trace 输入数据
    input_data = {
        "chapter_id": chapter_id,
        "course_id": course_id,
        "user_id": user_id,
    }
    
    if trace:
        trace.update(input=input_data)
    
    logger.info(f"开始生成词云: chapter={chapter_id}")
    
    config = config or {}
    width = config.get("width", 800)
    height = config.get("height", 400)
    max_words = config.get("max_words", 100)
    
    error_occurred = None
    
    try:
        # TODO: 实现实际的词云生成逻辑
        # 1. 获取章节内容
        # 2. 分词和统计
        # 3. 生成词云图片
        # 4. 上传到存储并返回 URL
        
        result = {
            "image_url": f"/static/wordcloud/{chapter_id}.png",
            "created_at": datetime.utcnow().isoformat(),
            "config": {
                "width": width,
                "height": height,
                "max_words": max_words,
            }
        }
        
        logger.info(f"词云生成完成: chapter={chapter_id}")
        return result
        
    except Exception as e:
        error_occurred = str(e)
        raise
    finally:
        # 记录 trace
        output_data = {"config": {"width": width, "height": height, "max_words": max_words}}
        _finish_trace(langfuse_client, trace, start_time, input_data, output_data, error_occurred)


def generate_knowledge_graph(
    chapter_id: str,
    course_id: str,
    user_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成知识图谱
    
    基于章节内容提取实体和关系，生成知识图谱。
    
    Args:
        chapter_id: 章节 ID
        course_id: 课程 ID
        user_id: 用户 ID（可选）
        config: 配置参数（可选）
            - entity_types: 要提取的实体类型
            - relation_types: 要提取的关系类型
    
    Returns:
        包含图谱数据的字典
    """
    # 创建 trace
    langfuse_client, trace, start_time = _create_trace("generate_knowledge_graph", ["task", "knowledge_graph"])
    
    # 准备 trace 输入数据
    input_data = {
        "chapter_id": chapter_id,
        "course_id": course_id,
        "user_id": user_id,
    }
    
    if trace:
        trace.update(input=input_data)
    
    logger.info(f"开始生成知识图谱: chapter={chapter_id}")
    
    config = config or {}
    entity_types = config.get("entity_types", ["概念", "方法", "工具"])
    relation_types = config.get("relation_types", ["包含", "依赖", "相关"])
    
    error_occurred = None
    
    try:
        # TODO: 实现实际的知识图谱生成逻辑
        # 1. 获取章节内容
        # 2. 使用 LLM 提取实体和关系
        # 3. 构建图谱数据结构
        # 4. 生成可视化图片
        
        result = {
            "graph_url": f"/static/knowledge_graph/{chapter_id}.png",
            "nodes": [],
            "edges": [],
            "created_at": datetime.utcnow().isoformat(),
            "config": {
                "entity_types": entity_types,
                "relation_types": relation_types,
            }
        }
        
        logger.info(f"知识图谱生成完成: chapter={chapter_id}")
        return result
        
    except Exception as e:
        error_occurred = str(e)
        raise
    finally:
        # 记录 trace
        output_data = {"config": {"entity_types": entity_types, "relation_types": relation_types}}
        _finish_trace(langfuse_client, trace, start_time, input_data, output_data, error_occurred)


def generate_quiz(
    chapter_id: str,
    course_id: str,
    user_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成 Quiz 题目
    
    基于章节内容使用 LLM 自动生成测验题目。
    
    Args:
        chapter_id: 章节 ID
        course_id: 课程 ID
        user_id: 用户 ID（可选）
        config: 配置参数（可选）
            - count: 题目数量
            - question_types: 题目类型列表
            - difficulty: 难度级别
    
    Returns:
        包含题目列表的字典
    """
    # 创建 trace
    langfuse_client, trace, start_time = _create_trace("generate_quiz", ["task", "quiz"])
    
    # 准备 trace 输入数据
    input_data = {
        "chapter_id": chapter_id,
        "course_id": course_id,
        "user_id": user_id,
    }
    
    if trace:
        trace.update(input=input_data)
    
    logger.info(f"开始生成 Quiz: chapter={chapter_id}")
    
    config = config or {}
    count = config.get("count", 5)
    question_types = config.get("question_types", ["single_choice", "multiple_choice"])
    difficulty = config.get("difficulty", "medium")
    
    error_occurred = None
    
    try:
        # TODO: 实现实际的 Quiz 生成逻辑
        # 1. 获取章节内容
        # 2. 调用 LLM 生成题目
        # 3. 解析和验证题目格式
        # 4. 保存到数据库
        
        result = {
            "questions": [],
            "count": count,
            "created_at": datetime.utcnow().isoformat(),
            "config": {
                "question_types": question_types,
                "difficulty": difficulty,
            }
        }
        
        logger.info(f"Quiz 生成完成: chapter={chapter_id}, count={count}")
        return result
        
    except Exception as e:
        error_occurred = str(e)
        raise
    finally:
        # 记录 trace
        output_data = {"count": count, "config": {"question_types": question_types, "difficulty": difficulty}}
        _finish_trace(langfuse_client, trace, start_time, input_data, output_data, error_occurred)


def index_chapter(
    chapter_id: str,
    course_id: str,
    chapter_file: str,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    索引单个章节到向量数据库
    
    版本控制机制：
    1. 先写入新版本的 chunks
    2. 成功后删除该章节的旧版本 chunks
    3. 查询时默认只返回当前版本的数据
    
    Args:
        chapter_id: 章节 ID（或 temp_ref）
        course_id: 课程 ID（目录名）
        chapter_file: 章节文件路径
        config: 索引配置
            - chunking_strategy: 切分策略
            - chunk_size: 块大小
            - chunk_overlap: 重叠大小
            - code_block_strategy: 代码块处理策略
            - clear_existing: 是否清除已有索引（包括其他章节）
    
    Returns:
        索引结果
    """
    langfuse_client, trace, start_time = _create_trace("index_chapter", ["task", "rag", "index"])
    
    input_data = {
        "chapter_id": chapter_id,
        "course_id": course_id,
        "chapter_file": chapter_file,
    }
    
    if trace:
        trace.update(input=input_data)
    
    logger.info(f"开始索引章节: chapter={chapter_id}, course={course_id}")
    
    config = config or {}
    clear_existing = config.get("clear_existing", False)
    
    error_occurred = None
    
    try:
        from pathlib import Path
        
        rag_service = RAGService.get_instance()
        
        # /app/app/tasks/jobs.py -> /app/courses
        courses_dir = Path(__file__).parent.parent.parent / "courses"
        chapter_path = courses_dir / course_id / chapter_file
        
        if not chapter_path.exists():
            raise ValueError(f"章节文件不存在: {chapter_path}")
        
        content = chapter_path.read_text(encoding="utf-8")
        
        collection_name = normalize_collection_name(f"course_local_{course_id}")
        
        store = ChromaVectorStore(
            collection_name=collection_name,
            persist_directory=rag_service.persist_directory
        )
        
        if clear_existing:
            try:
                store.delete_collection()
                store = ChromaVectorStore(
                    collection_name=collection_name,
                    persist_directory=rag_service.persist_directory
                )
            except Exception:
                pass
        
        # 获取当前章节的旧版本 chunk IDs（在写入新数据之前）
        source_file = f"{course_id}/{chapter_file}"
        legacy_chunk_ids = store.get_legacy_chunk_ids(source_file=source_file)
        
        if config.get("chunking_strategy"):
            from app.rag.chunking import SemanticChunkingStrategy
            rag_service.chunking_strategy = SemanticChunkingStrategy(
                min_chunk_size=config.get("min_chunk_size", 100),
                max_chunk_size=config.get("chunk_size", 1000),
                overlap_size=config.get("chunk_overlap", 200)
            )
        
        import asyncio
        chunk_count = asyncio.run(rag_service.index_course_content(
            content=content,
            course_id=course_id,
            chapter_id=source_file,  # 使用 source_file 作为章节标识，用于过滤
            chapter_title=chapter_file,
            source_file=source_file,
            clear_existing=False  # 不再清除，因为我们已经有版本控制
        ))
        
        # 新版本写入成功后，删除旧版本数据
        if legacy_chunk_ids:
            store.delete_chunks(legacy_chunk_ids)
            logger.info(f"已删除 {len(legacy_chunk_ids)} 个旧版本 chunks: {source_file}")
        
        db = SessionLocal()
        try:
            # 优先按 temp_ref 查询（因为 chapter_id 参数实际传入的是 temp_ref 格式）
            kb_config = db.query(ChapterKBConfig).filter(
                ChapterKBConfig.temp_ref == chapter_id
            ).first()
            
            if not kb_config:
                kb_config = db.query(ChapterKBConfig).filter(
                    ChapterKBConfig.chapter_id == chapter_id
                ).first()
            
            if kb_config:
                kb_config.index_status = "indexed"
                kb_config.chunk_count = chunk_count
                kb_config.indexed_at = datetime.utcnow()
                kb_config.updated_at = datetime.utcnow()
                kb_config.current_task_id = None
                db.commit()
                logger.info(f"更新章节索引状态: temp_ref={chapter_id}, status=indexed, chunks={chunk_count}")
            else:
                logger.warning(f"未找到章节配置记录: temp_ref={chapter_id}")
        except Exception as e:
            logger.error(f"更新章节索引状态失败: {e}")
        finally:
            db.close()
        
        result = {
            "chapter_id": chapter_id,
            "chunk_count": chunk_count,
            "legacy_chunks_removed": len(legacy_chunk_ids),
            "status": "success",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"章节索引完成: chapter={chapter_id}, chunks={chunk_count}, removed={len(legacy_chunk_ids)}")
        return result
        
    except Exception as e:
        error_occurred = str(e)
        
        try:
            db = SessionLocal()
            kb_config = db.query(ChapterKBConfig).filter(
                ChapterKBConfig.chapter_id == chapter_id
            ).first()
            if not kb_config:
                kb_config = db.query(ChapterKBConfig).filter(
                    ChapterKBConfig.temp_ref == chapter_id
                ).first()
            if kb_config:
                kb_config.index_status = "failed"
                kb_config.index_error = str(e)
                kb_config.updated_at = datetime.utcnow()
                kb_config.current_task_id = None
                db.commit()
            db.close()
        except Exception:
            pass
        
        raise
    finally:
        output_data = {"chunk_count": 0, "status": "failed" if error_occurred else "success"}
        _finish_trace(langfuse_client, trace, start_time, input_data, output_data, error_occurred)


def index_course(
    course_id: str,
    chapters: list,
    config: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    批量索引课程下所有章节
    
    Args:
        course_id: 课程 ID（目录名）
        chapters: 章节列表 [{"chapter_id": "...", "chapter_file": "..."}, ...]
        config: 索引配置（传递给 index_chapter）
        task_id: 任务 ID（用于分布式锁）
    
    Returns:
        批量索引结果
    """
    langfuse_client, trace, start_time = _create_trace("index_course", ["task", "rag", "index", "batch"])
    
    input_data = {
        "course_id": course_id,
        "chapter_count": len(chapters),
    }
    
    if trace:
        trace.update(input=input_data)
    
    logger.info(f"开始批量索引课程: course={course_id}, chapters={len(chapters)}")
    
    # 尝试获取课程级别的分布式锁
    lock_id = task_id or str(uuid.uuid4())
    if not acquire_course_lock(course_id, lock_id, ttl=3600):
        logger.warning(f"课程 {course_id} 正在被其他任务处理，跳过")
        return {
            "course_id": course_id,
            "total_chapters": 0,
            "success_count": 0,
            "failed_count": 0,
            "results": [],
            "error": "课程正在被其他任务处理",
            "created_at": datetime.utcnow().isoformat(),
        }
    
    try:
        config = config or {}
        results = []
        success_count = 0
        failed_count = 0
        first_chapter = True
        
        for chapter_info in chapters:
            try:
                # 只在第一个章节时清除整个 collection
                chapter_config = config.copy()
                if first_chapter:
                    chapter_config["clear_existing"] = config.get("clear_existing", False)
                    first_chapter = False
                else:
                    chapter_config["clear_existing"] = False
                
                result = index_chapter(
                    chapter_id=chapter_info.get("temp_ref") or chapter_info.get("chapter_id"),
                    course_id=course_id,
                    chapter_file=chapter_info["chapter_file"],
                    config=chapter_config
                )
                results.append({
                    "chapter_id": chapter_info.get("chapter_id"),
                    "status": "success",
                    "chunk_count": result.get("chunk_count", 0)
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "chapter_id": chapter_info.get("chapter_id"),
                    "status": "failed",
                    "error": str(e)
                })
                failed_count += 1
        
        result = {
            "course_id": course_id,
            "total_chapters": len(chapters),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"课程批量索引完成: course={course_id}, success={success_count}, failed={failed_count}")
        
        output_data = {"success_count": success_count, "failed_count": failed_count}
        _finish_trace(langfuse_client, trace, start_time, input_data, output_data)
        
        return result
    
    finally:
        release_course_lock(course_id, lock_id)
