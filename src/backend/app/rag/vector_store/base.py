from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union


class VectorStore(ABC):
    @abstractmethod
    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """
        添加 chunks 到向量存储
        
        Args:
            chunks: Chunk 列表，每个包含 id, text, metadata
            embeddings: 对应的向量列表，shape: (n_chunks, dim)
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: Union[List[float], Any],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量
        
        Args:
            query_embedding: 查询向量，shape: (dim,)
            top_k: 返回 Top K 结果
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
