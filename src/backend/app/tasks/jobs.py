"""
异步任务函数

定义可在后台执行的任务函数，包括：
- 词云生成
- 知识图谱生成
- Quiz 自动生成

所有任务函数都会被 Langfuse 追踪。
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

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
    
    trace.span(
        name=f"{trace.name}_call",
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
