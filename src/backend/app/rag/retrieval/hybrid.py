"""混合检索模块（Extra功能）- 向量检索 + 关键词检索"""

from typing import List, Dict, Any, Optional
import numpy as np
from collections import Counter

from .retriever import RAGRetriever, RetrievalResult


class HybridRetriever:
    """混合检索器 - 结合向量检索和关键词检索"""
    
    def __init__(
        self,
        vector_retriever: RAGRetriever,
        keyword_retriever: Optional['KeywordRetriever'] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        """
        Args:
            vector_retriever: 向量检索器
            keyword_retriever: 关键词检索器（BM25等）
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
        """
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
    
    async def retrieve(
        self,
        query: str,
        course_id: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[RetrievalResult]:
        """
        混合检索
        
        Args:
            query: 查询文本
            course_id: 课程ID
            top_k: 返回Top K结果
            filters: 元数据过滤条件
            score_threshold: 相似度阈值
        
        Returns:
            检索结果列表
        """
        # 向量检索
        vector_results = await self.vector_retriever.retrieve(
            query, course_id, top_k * 2, filters, score_threshold
        )
        
        # 关键词检索（如果可用）
        keyword_results = []
        if self.keyword_retriever:
            keyword_results = await self.keyword_retriever.retrieve(
                query, course_id, top_k * 2, filters
            )
        
        # 融合结果
        merged_results = self._merge_results(
            vector_results,
            keyword_results,
            top_k
        )
        
        return merged_results
    
    def _merge_results(
        self,
        vector_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """融合向量检索和关键词检索结果"""
        # 构建chunk_id到结果的映射
        result_map: Dict[str, RetrievalResult] = {}
        
        # 添加向量检索结果
        for result in vector_results:
            result_map[result.chunk_id] = result
            # 归一化向量分数到[0, 1]
            result.score = result.score * self.vector_weight
        
        # 添加关键词检索结果并融合分数
        for result in keyword_results:
            if result.chunk_id in result_map:
                # 融合分数
                result_map[result.chunk_id].score += result.score * self.keyword_weight
            else:
                # 归一化关键词分数
                result.score = result.score * self.keyword_weight
                result_map[result.chunk_id] = result
        
        # 按融合后的分数排序
        sorted_results = sorted(
            result_map.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        return sorted_results[:top_k]


class KeywordRetriever:
    """简单关键词检索器（基于TF-IDF或BM25）"""
    
    def __init__(self, chunks: Dict[str, str]):
        """
        Args:
            chunks: chunk_id -> chunk_text 映射
        """
        self.chunks = chunks
        self._build_index()
    
    def _build_index(self):
        """构建关键词索引"""
        # 简单的倒排索引
        self.index: Dict[str, List[str]] = {}
        
        for chunk_id, text in self.chunks.items():
            # 简单分词（实际可以使用jieba等）
            words = self._tokenize(text)
            for word in words:
                if word not in self.index:
                    self.index[word] = []
                self.index[word].append(chunk_id)
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 移除标点，分割
        import re
        words = re.findall(r'\w+', text.lower())
        return words
    
    async def retrieve(
        self,
        query: str,
        course_id: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """关键词检索"""
        query_words = self._tokenize(query)
        
        # 计算每个chunk的相关性分数
        scores: Dict[str, float] = {}
        
        for word in query_words:
            if word in self.index:
                for chunk_id in self.index[word]:
                    scores[chunk_id] = scores.get(chunk_id, 0) + 1
        
        # 归一化分数
        if scores:
            max_score = max(scores.values())
            scores = {k: v / max_score for k, v in scores.items()}
        
        # 排序并返回Top K
        sorted_chunk_ids = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        results = []
        for chunk_id, score in sorted_chunk_ids:
            results.append(RetrievalResult(
                chunk_id=chunk_id,
                text=self.chunks[chunk_id],
                metadata={},
                score=score,
                source="关键词检索"
            ))
        
        return results
