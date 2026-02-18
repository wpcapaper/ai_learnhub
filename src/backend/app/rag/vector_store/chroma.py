from typing import List, Dict, Any, Optional, Union
import chromadb
from chromadb.config import Settings
import os

from .base import VectorStore


class ChromaVectorStore(VectorStore):
    """ChromaDB 向量存储实现"""
    
    def __init__(
        self,
        collection_name: str,
        persist_directory: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        self.collection_name = collection_name
        
        # 优先使用远程服务，其次使用本地持久化
        if host and port:
            self.client = chromadb.HttpClient(host=host, port=port)
        else:
            if persist_directory is None:
                persist_directory = os.path.join(
                    os.path.dirname(__file__),
                    "../../../data/chroma"
                )
                os.makedirs(persist_directory, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        
        # 使用余弦相似度
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """添加 chunks 和对应的向量"""
        if len(chunks) != len(embeddings):
            raise ValueError(f"chunks({len(chunks)}) 和 embeddings({len(embeddings)}) 数量不匹配")
        
        ids = [chunk["id"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk.get("metadata", {}) for chunk in chunks]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    def search(
        self,
        query_embedding: Union[List[float], Any],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似向量，返回 Top K 结果"""
        # 处理 numpy 数组转 list
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        
        # 构建 ChromaDB 过滤条件
        where = None
        if filters:
            where = {}
            for key, value in filters.items():
                if isinstance(value, list):
                    where[key] = {"$in": value}
                else:
                    where[key] = value
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        # 格式化返回结果
        formatted = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                # 余弦距离转相似度（1 - distance）
                distance = results["distances"][0][i] if results["distances"] else 0.0
                formatted.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1.0 - distance
                })
        
        return formatted
    
    def delete_collection(self) -> None:
        """删除集合并重新创建空集合"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def get_collection_size(self) -> int:
        """获取集合中的向量数量"""
        return self.collection.count()
    
    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """删除指定的 chunks"""
        self.collection.delete(ids=chunk_ids)
