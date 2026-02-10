"""ChromaDB向量存储实现"""

from typing import List, Dict, Any, Optional
import numpy as np
import chromadb
from chromadb.config import Settings
import os

from .base import VectorStore


class ChromaVectorStore(VectorStore):
    """ChromaDB向量存储"""
    
    def __init__(
        self,
        collection_name: str,
        persist_directory: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        """
        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录（本地模式）
            host: 服务器地址（客户端模式）
            port: 服务器端口（客户端模式）
        """
        self.collection_name = collection_name
        
        # 初始化客户端
        if host and port:
            # 客户端模式
            self.client = chromadb.HttpClient(
                host=host,
                port=port
            )
        else:
            # 本地模式
            if persist_directory is None:
                # 默认目录
                persist_directory = os.path.join(
                    os.path.dirname(__file__),
                    "../../../data/chroma"
                )
                os.makedirs(persist_directory, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
    
    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: np.ndarray
    ) -> None:
        """添加chunks"""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks和embeddings数量不匹配")
        
        ids = [chunk["id"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk.get("metadata", {}) for chunk in chunks]
        
        # 转换embeddings为list
        embeddings_list = embeddings.tolist()
        
        # 添加到集合
        self.collection.add(
            ids=ids,
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas
        )
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        # 构建查询条件
        query_embedding_list = query_embedding.tolist()
        
        # 构建where条件（ChromaDB的过滤语法）
        where = None
        if filters:
            where = {}
            for key, value in filters.items():
                if isinstance(value, list):
                    where[key] = {"$in": value}
                else:
                    where[key] = value
        
        # 执行查询
        results = self.collection.query(
            query_embeddings=[query_embedding_list],
            n_results=top_k,
            where=where
        )
        
        # 格式化结果
        formatted_results = []
        
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0  # 距离转相似度
                })
        
        return formatted_results
    
    def delete_collection(self) -> None:
        """删除集合"""
        self.client.delete_collection(name=self.collection_name)
        # 重新创建空集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def get_collection_size(self) -> int:
        """获取集合大小"""
        return self.collection.count()
    
    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """删除指定的chunks"""
        self.collection.delete(ids=chunk_ids)
    
    def update_chunk(
        self,
        chunk_id: str,
        text: Optional[str] = None,
        embedding: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """更新chunk"""
        # ChromaDB不支持直接更新，需要先删除再添加
        self.collection.delete(ids=[chunk_id])
        
        if text is not None or embedding is not None:
            update_data = {}
            if text is not None:
                update_data["documents"] = [text]
            if embedding is not None:
                update_data["embeddings"] = [embedding.tolist()]
            if metadata is not None:
                update_data["metadatas"] = [metadata]
            
            self.collection.add(
                ids=[chunk_id],
                **update_data
            )
