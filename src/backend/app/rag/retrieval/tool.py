from typing import List

from .retriever import RetrievalResult
from ..service import RAGService


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
