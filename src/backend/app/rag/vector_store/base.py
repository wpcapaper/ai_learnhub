"""向量存储抽象接口"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np


class VectorStore(ABC):
    """向量存储抽象基类"""
    
    @abstractmethod
    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: np.ndarray
    ) -> None:
        """
        添加chunks到向量存储
        
        Args:
            chunks: Chunk列表，每个包含 id, text, metadata
            embeddings: 对应的向量数组 (n_chunks, dim)
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量
        
        Args:
            query_embedding: 查询向量 (dim,)
            top_k: 返回Top K结果
            filters: 元数据过滤条件
        
        Returns:
            结果列表，每个包含 id, text, metadata, score
        """
        pass
    
    @abstractmethod
    def delete_collection(self) -> None:
        """删除集合"""
        pass
    
    @abstractmethod
    def get_collection_size(self) -> int:
        """获取集合大小"""
        pass
