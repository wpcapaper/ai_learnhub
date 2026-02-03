"""RAG检索器"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np

from ..embedding.models import EmbeddingModel
from ..vector_store.base import VectorStore


@dataclass
class RetrievalResult:
    """检索结果"""
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    score: float
    source: str  # 来源信息（章节、位置等）


class RAGRetriever:
    """RAG检索器"""
    
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore
    ):
        """
        Args:
            embedding_model: Embedding模型
            vector_store: 向量存储
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
    
    async def retrieve(
        self,
        query: str,
        course_id: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[RetrievalResult]:
        """
        检索相关文档片段
        
        Args:
            query: 查询文本
            course_id: 课程ID
            top_k: 返回Top K结果
            filters: 元数据过滤条件
            score_threshold: 相似度阈值
        
        Returns:
            检索结果列表
        """
        # 编码查询
        query_embedding = self.embedding_model.encode([query])[0]
        
        # 构建过滤条件
        search_filters = filters or {}
        if course_id:
            search_filters["course_id"] = course_id
        
        # 向量检索
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # 多检索一些，用于后续过滤
            filters=search_filters if search_filters else None
        )
        
        # 转换为RetrievalResult并过滤
        retrieval_results = []
        for result in results:
            if result["score"] >= score_threshold:
                # 构建来源信息
                metadata = result.get("metadata", {})
                source = self._build_source_info(metadata)
                
                retrieval_results.append(RetrievalResult(
                    chunk_id=result["id"],
                    text=result["text"],
                    metadata=metadata,
                    score=result["score"],
                    source=source
                ))
        
        # 只返回top_k
        return retrieval_results[:top_k]
    
    def _build_source_info(self, metadata: Dict[str, Any]) -> str:
        """构建来源信息字符串"""
        parts = []
        
        if metadata.get("chapter_title"):
            parts.append(metadata["chapter_title"])
        elif metadata.get("chapter_id"):
            parts.append(f"章节 {metadata['chapter_id']}")
        
        if metadata.get("position") is not None:
            parts.append(f"位置 {metadata['position']}")
        
        return " | ".join(parts) if parts else "未知来源"
