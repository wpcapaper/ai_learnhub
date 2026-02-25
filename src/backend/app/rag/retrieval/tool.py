from dataclasses import dataclass
import json
from typing import List, Optional

from .retriever import RetrievalResult


@dataclass
class RagChunk:
    chunk_id: str
    score: float
    text: str
    source_file: Optional[str] = None
    position: Optional[int] = None
    content_type: Optional[str] = None


async def retrieve_course_content(
    query: str,
    course_id: str,
    top_k: int = 5
) -> str:
    """
    从课程内容中检索相关信息（供 Agent 调用的工具）
    
    Args:
        query: 用户问题
        course_id: 课程 ID
        top_k: 返回 Top K 个相关片段
    
    Returns:
        格式化的检索结果，包含原文引用
    """
    from ..service import RAGService
    
    rag_service = RAGService.get_instance()
    results = await rag_service.retrieve(query, course_id, top_k)
    
    if not results:
        return "未找到相关内容。"
    
    # 格式化结果供 Agent 使用
    formatted = [f"找到 {len(results)} 个相关片段：\n"]
    for i, r in enumerate(results, 1):
        formatted.append(f"\n【片段 {i}】")
        formatted.append(f"来源：{r.source}")
        formatted.append(f"相似度：{r.score:.3f}")
        formatted.append(f"内容：\n{r.text}\n")
        formatted.append("---")
    
    return "\n".join(formatted)


def format_results_for_agent(results: List[RetrievalResult]) -> str:
    """
    格式化检索结果为Agent可用的格式
    
    Args:
        results: 检索结果列表
    
    Returns:
        格式化后的字符串
    """
    if not results:
        return "未找到相关内容。"
    
    formatted_parts = []
    
    for i, result in enumerate(results, 1):
        formatted_parts.append(f"\n[引用 {i}]")
        formatted_parts.append(f"来源：{result.source}")
        formatted_parts.append(f"内容：{result.text}")
    
    return "\n".join(formatted_parts)


async def retrieve_course_chunks(
    query: str,
    course_code: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    chapter_source_file: Optional[str] = None,
    chapter_order: Optional[int] = None
) -> List[RagChunk]:
    from ..service import RAGService
    from app.core.paths import get_course_json_path

    source_file = _resolve_source_file(course_code, chapter_source_file, chapter_order, get_course_json_path)
    filters = {"source_file": source_file} if source_file else None

    rag_service = RAGService.get_instance()
    results = await rag_service.retrieve(
        query=query,
        code=course_code,
        top_k=top_k,
        score_threshold=score_threshold,
        filters=filters,
    )

    chunks: List[RagChunk] = []
    for result in results:
        metadata = result.metadata if hasattr(result, "metadata") else {}
        chunks.append(RagChunk(
            chunk_id=result.chunk_id,
            score=result.score,
            text=result.text,
            source_file=metadata.get("source_file"),
            position=metadata.get("position"),
            content_type=metadata.get("content_type"),
        ))
    return chunks


async def retrieve_chapter_chunks(
    query: str,
    course_code: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    chapter_source_file: Optional[str] = None,
    chapter_order: Optional[int] = None
) -> List[RagChunk]:
    return await retrieve_course_chunks(
        query=query,
        course_code=course_code,
        top_k=top_k,
        score_threshold=score_threshold,
        chapter_source_file=chapter_source_file,
        chapter_order=chapter_order,
    )


def build_rag_context(chunks: List[RagChunk], max_context_chars: int = 3000) -> str:
    if not chunks:
        return ""
    parts: List[str] = []
    total_chars = 0
    for idx, chunk in enumerate(chunks, 1):
        header = f"[引用 {idx}] 来源: {chunk.source_file or '未知'} / 位置: {chunk.position if chunk.position is not None else '-'}"
        block = f"{header}\n{chunk.text}\n"
        if total_chars + len(block) > max_context_chars:
            break
        parts.append(block)
        total_chars += len(block)
    return "\n".join(parts).strip()


def _resolve_source_file(
    course_code: str,
    chapter_source_file: Optional[str],
    chapter_order: Optional[int],
    get_course_json_path
) -> Optional[str]:
    if chapter_source_file:
        return chapter_source_file
    if chapter_order is None:
        return None

    course_json_path = get_course_json_path(course_code)
    if not course_json_path.exists():
        return None

    try:
        with open(course_json_path, "r", encoding="utf-8") as f:
            course_data = json.load(f)
    except Exception:
        return None

    chapters = course_data.get("chapters", [])
    target_order = _normalize_order(chapter_order)
    for chapter in chapters:
        order_value = _normalize_order(chapter.get("sort_order", chapter.get("order")))
        if order_value == target_order:
            return chapter.get("file")

    if target_order is not None:
        index = target_order - 1
        if 0 <= index < len(chapters):
            return chapters[index].get("file")

    return None


def _normalize_order(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
