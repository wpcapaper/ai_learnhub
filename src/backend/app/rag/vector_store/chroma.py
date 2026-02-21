from typing import List, Dict, Any, Optional, Union
import chromadb
from chromadb.config import Settings
import os

from .base import VectorStore
from ..chunking.strategies import CURRENT_STRATEGY_VERSION


class ChromaVectorStore(VectorStore):
    """ChromaDB 向量存储实现
    
    版本控制：
    - 查询时默认只返回当前策略版本的 chunks
    - 可通过 filter_legacy=False 禁用版本过滤
    - 提供清理旧版本数据的方法
    """
    
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
        embeddings: List[Any]
    ) -> None:
        """添加 chunks 和对应的向量"""
        if len(chunks) != len(embeddings):
            raise ValueError(f"chunks({len(chunks)}) 和 embeddings({len(embeddings)}) 数量不匹配")
        
        ids = [chunk["id"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk.get("metadata", {}) for chunk in chunks]
        
        # 确保 embeddings 是 list 格式
        processed_embeddings = []
        for emb in embeddings:
            if emb is not None and hasattr(emb, 'tolist'):
                processed_embeddings.append(emb.tolist())
            else:
                processed_embeddings.append(emb)
        
        self.collection.add(
            ids=ids,
            embeddings=processed_embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    def search(
        self,
        query_embedding: Union[List[float], Any],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        filter_legacy: bool = True
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
    
    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """
        获取集合中的所有文档块（用于管理页面展示）
        
        返回格式：
        [
            {
                "id": "chunk_id",
                "content": "文档块文本内容",
                "metadata": {
                    "source_file": "xxx.md",
                    "content_type": "text/code/summary",
                    "is_active": True,
                    ...
                }
            },
            ...
        ]
        """
        # 获取所有数据（ChromaDB 限制单次最多获取的数量）
        all_chunks = []
        limit = 1000
        offset = 0
        
        while True:
            # 使用 get 方法获取数据
            results = self.collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"]
            )
            
            if not results["ids"]:
                break
            
            for i in range(len(results["ids"])):
                all_chunks.append({
                    "id": results["ids"][i],
                    "content": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
            
            # 如果获取的数量小于 limit，说明已经获取完所有数据
            if len(results["ids"]) < limit:
                break
            
            offset += limit
        
        return all_chunks
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取单个文档块"""
        try:
            results = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"]
            )
            
            if not results["ids"]:
                return None
            
            return {
                "id": results["ids"][0],
                "text": results["documents"][0] if results["documents"] else "",
                "metadata": results["metadatas"][0] if results["metadatas"] else {}
            }
        except Exception:
            return None
    
    def get_chunks_with_embeddings(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        """获取指定 chunks 及其 embeddings（用于同步）"""
        if not chunk_ids:
            return []
        
        results = self.collection.get(
            ids=chunk_ids,
            include=["documents", "metadatas", "embeddings"]
        )
        
        chunks = []
        embeddings = results.get("embeddings")
        
        for i in range(len(results["ids"])):
            emb = None
            if embeddings is not None and len(embeddings) > i:
                emb = embeddings[i]
                if hasattr(emb, 'tolist'):
                    emb = emb.tolist()
            
            chunks.append({
                "id": results["ids"][i],
                "content": results["documents"][i] if results["documents"] else "",
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
                "embedding": emb
            })
        
        return chunks
    
    def get_legacy_chunk_ids(self, source_file: Optional[str] = None) -> List[str]:
        """
        获取旧版本 chunks 的 ID 列表
        
        Args:
            source_file: 可选，限定特定源文件
        
        Returns:
            旧版本 chunk ID 列表
        """
        # ChromaDB 不支持 $ne 操作符，改为获取所有数据后在内存中过滤
        all_chunks = self.get_all_chunks()
        
        legacy_ids = []
        for chunk in all_chunks:
            metadata = chunk.get("metadata", {})
            version = metadata.get("strategy_version")
            file = metadata.get("source_file")
            
            # 筛选条件：版本不匹配当前版本
            is_legacy = version is not None and version != CURRENT_STRATEGY_VERSION
            
            # 如果指定了 source_file，还要匹配文件
            if source_file:
                if file != source_file:
                    continue
            
            if is_legacy:
                legacy_ids.append(chunk["id"])
        
        return legacy_ids
    
    def delete_legacy_chunks(self, source_file: Optional[str] = None) -> int:
        """
        删除旧版本的 chunks
        
        Args:
            source_file: 可选，限定特定源文件
        
        Returns:
            删除的 chunk 数量
        """
        legacy_ids = self.get_legacy_chunk_ids(source_file)
        
        if legacy_ids:
            self.collection.delete(ids=legacy_ids)
        
        return len(legacy_ids)
    
    def get_version_stats(self) -> Dict[str, int]:
        """
        获取各版本 chunk 的统计信息
        
        Returns:
            {"markdown-v1.0": 100, "markdown-v0.9": 20, ...}
        """
        all_chunks = self.get_all_chunks()
        stats = {}
        
        for chunk in all_chunks:
            version = chunk.get("metadata", {}).get("strategy_version", "unknown")
            stats[version] = stats.get(version, 0) + 1
        
        return stats
