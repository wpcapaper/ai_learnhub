"""
异步任务函数

定义可在后台执行的任务函数，包括：
- 词云生成
- 知识图谱生成
- Quiz 自动生成

所有任务函数都会被 Langfuse 追踪。
"""

import logging
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.rag.service import RAGService

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
    course_code: str,
    chapter_file: Optional[str] = None,
    top_k: int = 100,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    异步生成词云
    
    支持课程级和章节级词云生成。
    
    Args:
        course_code: 课程代码（目录名）
        chapter_file: 章节文件名（不含扩展名），为 None 时生成课程级词云
        top_k: 提取的关键词数量
        config: 配置参数（可选，保留兼容性）
    
    Returns:
        词云生成结果
    """
    from pathlib import Path
    from app.services.wordcloud_service import WordcloudService
    
    # 创建 trace
    langfuse_client, trace, start_time = _create_trace("generate_wordcloud", ["task", "wordcloud"])
    
    # 准备 trace 输入数据
    input_data = {
        "course_code": course_code,
        "chapter_file": chapter_file,
        "top_k": top_k,
    }
    
    if trace:
        trace.update(input=input_data)
    
    error_occurred = None
    
    try:
        # 获取课程目录
        markdown_dir = Path(os.environ.get("MARKDOWN_COURSES_DIR", "markdown_courses"))
        course_dir = markdown_dir / course_code
        
        if not course_dir.exists():
            raise ValueError(f"课程目录不存在: {course_code}")
        
        wc_service = WordcloudService(courses_dir=str(markdown_dir))
        
        if chapter_file:
            # 生成章节词云
            chapter_path = course_dir / f"{chapter_file}.md"
            if not chapter_path.exists():
                raise ValueError(f"章节文件不存在: {chapter_path}")
            
            logger.info(f"开始生成章节词云: course={course_code}, chapter={chapter_file}")
            wordcloud_data = wc_service.generate_chapter_wordcloud(chapter_path, top_k=top_k)
            
            result = {
                "success": True,
                "course_code": course_code,
                "chapter_file": chapter_file,
                "words_count": len(wordcloud_data.get("words", [])),
                "generated_at": wordcloud_data.get("generated_at"),
            }
            
            logger.info(f"章节词云生成完成: chapter={chapter_file}, words_count={result['words_count']}")
        else:
            # 生成课程词云
            logger.info(f"开始生成课程词云: course={course_code}")
            wordcloud_data = wc_service.generate_course_wordcloud(course_dir, top_k=top_k)
            
            result = {
                "success": True,
                "course_code": course_code,
                "words_count": len(wordcloud_data.get("words", [])),
                "generated_at": wordcloud_data.get("generated_at"),
            }
            
            logger.info(f"课程词云生成完成: course={course_code}, words_count={result['words_count']}")
        
        return result
        
    except Exception as e:
        error_occurred = str(e)
        logger.error(f"词云生成失败: course={course_code}, chapter={chapter_file}, error={str(e)}")
        raise
    finally:
        output_data = {"success": error_occurred is None}
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
    temp_ref: str,
    code: str,
    source_file: str,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    索引单个章节到向量数据库
    
    按照 RAG_ARCHITECTURE.md 规范：
    - Collection 命名：course_{code}_{kb_version}
    - 使用 code（课程目录名）和 source_file（章节文件路径）标识
    
    Args:
        temp_ref: 临时引用（格式：{code}/{source_file}，用于数据库记录）
        code: 课程代码（目录名）
        source_file: 章节文件路径（相对于课程目录）
        config: 索引配置
            - chunking_strategy: 切分策略
            - chunk_size: 块大小
            - chunk_overlap: 重叠大小
            - kb_version: 知识库版本号（默认从 course.json 读取）
    
    Returns:
        索引结果
    """
    langfuse_client, trace, start_time = _create_trace("index_chapter", ["task", "rag", "index"])
    
    input_data = {
        "temp_ref": temp_ref,
        "code": code,
        "source_file": source_file,
    }
    
    if trace:
        trace.update(input=input_data)
    
    logger.info(f"开始索引章节: code={code}, source_file={source_file}")
    
    config = config or {}
    kb_version = config.get("kb_version", 1)
    
    error_occurred = None
    
    try:
        from pathlib import Path
        import json
        
        # 尝试从 course.json 读取 kb_version（如果未指定）
        if not config.get("kb_version"):
            courses_dir = Path(__file__).parent.parent.parent / "courses"
            course_json_path = courses_dir / code / "course.json"
            if course_json_path.exists():
                with open(course_json_path, "r", encoding="utf-8") as f:
                    course_data = json.load(f)
                    kb_version = course_data.get("kb_version", 1)
        
        rag_service = RAGService.get_instance()
        
        # 读取章节文件
        courses_dir = Path(__file__).parent.parent.parent / "courses"
        chapter_path = courses_dir / code / source_file
        
        if not chapter_path.exists():
            raise ValueError(f"章节文件不存在: {chapter_path}")
        
        content = chapter_path.read_text(encoding="utf-8")
        
        # 配置切分策略（如果指定）
        if config.get("chunking_strategy"):
            from app.rag.chunking import SemanticChunkingStrategy
            rag_service.chunking_strategy = SemanticChunkingStrategy(
                min_chunk_size=config.get("min_chunk_size", 100),
                max_chunk_size=config.get("chunk_size", 1000),
                overlap_size=config.get("chunk_overlap", 200)
            )
        
        # 使用新 API 索引内容
        import asyncio
        chunk_count = asyncio.run(rag_service.index_course_content(
            content=content,
            code=code,
            source_file=source_file,
            kb_version=kb_version,
            clear_existing=False
        ))
        
        # 更新章节索引状态
        db = SessionLocal()
        try:
            kb_config = db.query(ChapterKBConfig).filter(
                ChapterKBConfig.temp_ref == temp_ref
            ).first()
            
            if kb_config:
                kb_config.index_status = "indexed"
                kb_config.chunk_count = chunk_count
                kb_config.indexed_at = datetime.utcnow()
                kb_config.updated_at = datetime.utcnow()
                kb_config.current_task_id = None
                db.commit()
                logger.info(f"更新章节索引状态: temp_ref={temp_ref}, status=indexed, chunks={chunk_count}")
            else:
                logger.warning(f"未找到章节配置记录: temp_ref={temp_ref}")
        except Exception as e:
            logger.error(f"更新章节索引状态失败: {e}")
        finally:
            db.close()
        
        result = {
            "temp_ref": temp_ref,
            "code": code,
            "source_file": source_file,
            "chunk_count": chunk_count,
            "kb_version": kb_version,
            "status": "success",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"章节索引完成: code={code}, source_file={source_file}, chunks={chunk_count}")
        return result
        
    except Exception as e:
        error_occurred = str(e)
        
        try:
            db = SessionLocal()
            kb_config = db.query(ChapterKBConfig).filter(
                ChapterKBConfig.temp_ref == temp_ref
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
    code: str,
    chapters: list,
    config: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    批量索引课程下所有章节
    
    按照 RAG_ARCHITECTURE.md 规范：
    - Collection 命名：course_{code}_{kb_version}
    - 使用 code（课程目录名）作为主标识符
    
    Args:
        code: 课程代码（目录名）
        chapters: 章节列表 [{"temp_ref": "...", "chapter_file": "..."}, ...]
        config: 索引配置（传递给 index_chapter）
            - kb_version: 知识库版本号
            - clear_existing: 是否清除已有索引
        task_id: 任务 ID（用于分布式锁）
    
    Returns:
        批量索引结果
    """
    langfuse_client, trace, start_time = _create_trace("index_course", ["task", "rag", "index", "batch"])
    
    input_data = {
        "code": code,
        "chapter_count": len(chapters),
    }
    
    if trace:
        trace.update(input=input_data)
    
    logger.info(f"开始批量索引课程: code={code}, chapters={len(chapters)}")
    
    # 尝试获取课程级别的分布式锁
    lock_id = task_id or str(uuid.uuid4())
    if not acquire_course_lock(code, lock_id, ttl=3600):
        logger.warning(f"课程 {code} 正在被其他任务处理，跳过")
        return {
            "code": code,
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
                if first_chapter and config.get("clear_existing", False):
                    # 清除操作在新版本中通过重建 collection 实现
                    chapter_config["clear_existing"] = True
                    first_chapter = False
                else:
                    chapter_config["clear_existing"] = False
                
                temp_ref = chapter_info.get("temp_ref") or f"{code}/{chapter_info['chapter_file']}"
                source_file = chapter_info.get("chapter_file")
                
                result = index_chapter(
                    temp_ref=temp_ref,
                    code=code,
                    source_file=source_file,
                    config=chapter_config
                )
                results.append({
                    "temp_ref": temp_ref,
                    "source_file": source_file,
                    "status": "success",
                    "chunk_count": result.get("chunk_count", 0)
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "temp_ref": chapter_info.get("temp_ref"),
                    "source_file": chapter_info.get("chapter_file"),
                    "status": "failed",
                    "error": str(e)
                })
                failed_count += 1
        
        result = {
            "code": code,
            "total_chapters": len(chapters),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"课程批量索引完成: code={code}, success={success_count}, failed={failed_count}")
        
        output_data = {"success_count": success_count, "failed_count": failed_count}
        _finish_trace(langfuse_client, trace, start_time, input_data, output_data)
        
        return result
    
    finally:
        release_course_lock(code, lock_id)
