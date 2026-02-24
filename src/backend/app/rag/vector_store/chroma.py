from typing import List, Dict, Any, Optional, Union
import chromadb
from chromadb.config import Settings
import os

from .base import VectorStore


class ChromaVectorStore(VectorStore):
    """ChromaDB 向量存储实现
    
    按照 RAG_ARCHITECTURE.md 规范：
    - Collection 命名：course_{code}_{kb_version}
    - Metadata 字段：code, source_file, position, char_start, char_end, content_type, char_count, estimated_tokens, kb_version
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
    
    def delete_by_source_file(self, source_file: str) -> int:
        """删除指定源文件的所有 chunks"""
        all_chunks = self.get_all_chunks()
        ids_to_delete = [
            chunk["id"] for chunk in all_chunks
            if chunk.get("metadata", {}).get("source_file") == source_file
        ]
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)
    
    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """获取集合中的所有文档块"""
        all_chunks = []
        limit = 1000
        offset = 0
        
        while True:
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
        """获取指定 chunks 及其 embeddings"""
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
