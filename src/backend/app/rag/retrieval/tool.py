"""为Agent提供的检索工具"""

from typing import Optional, List, TYPE_CHECKING

from .retriever import RetrievalResult

if TYPE_CHECKING:
    from ..service import RAGService


# 全局RAG服务实例（延迟初始化）
_rag_service: Optional['RAGService'] = None


def set_rag_service(rag_service: 'RAGService'):
    """设置RAG服务实例"""
    global _rag_service
    _rag_service = rag_service


async def retrieve_course_content(
    query: str,
    course_id: str,
    top_k: int = 5
) -> str:
    """
    从课程内容中检索相关信息（Agent Tool）
    
    Args:
        query: 用户问题
        course_id: 课程ID
        top_k: 返回top K个相关片段
    
    Returns:
        格式化的检索结果，包含原文引用
    """
    if _rag_service is None:
        raise RuntimeError("RAG服务未初始化，请先调用set_rag_service()")
    
    # 执行检索
    results = await _rag_service.retrieve(query, course_id, top_k)
    
    # 格式化结果
    if not results:
        return "未找到相关内容。"
    
    formatted_parts = []
    formatted_parts.append(f"找到 {len(results)} 个相关片段：\n")
    
    for i, result in enumerate(results, 1):
        formatted_parts.append(f"\n【片段 {i}】")
        formatted_parts.append(f"来源：{result.source}")
        formatted_parts.append(f"相似度：{result.score:.3f}")
        formatted_parts.append(f"内容：\n{result.text}\n")
        formatted_parts.append("---")
    
    return "\n".join(formatted_parts)


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
