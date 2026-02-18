"""重排序模块（Extra功能）"""

from typing import List
from sentence_transformers import CrossEncoder

from .retriever import RetrievalResult


class Reranker:
    """重排序器 - 使用交叉编码器提升精确度"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        """
        Args:
            model_name: 重排序模型名称
        """
        self.model = CrossEncoder(model_name)
    
    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = None
    ) -> List[RetrievalResult]:
        """
        对检索结果重排序
        
        Args:
            query: 查询文本
            results: 检索结果列表
            top_k: 返回Top K结果（None表示返回全部）
        
        Returns:
            重排序后的结果列表
        """
        if not results:
            return []
        
        # 构建查询-文档对
        pairs = [[query, result.text] for result in results]
        
        # 计算相关性分数
        scores = self.model.predict(pairs)
        
        # 按分数排序
        sorted_indices = sorted(
            range(len(results)),
            key=lambda i: scores[i],
            reverse=True
        )
        
        # 重新排序结果
        reranked = [results[i] for i in sorted_indices]
        
        # 更新分数
        for i, idx in enumerate(sorted_indices):
            reranked[i].score = float(scores[idx])
        
        # 返回Top K
        if top_k is not None:
            return reranked[:top_k]
        
        return reranked
