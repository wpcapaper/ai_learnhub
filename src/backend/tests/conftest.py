"""
Pytest 配置和通用 Fixtures

提供 Mock ChromaDB 和 Embedding 模型的 fixtures
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import List, Dict, Any
import tempfile
import shutil
import os


# ==================== Mock ChromaVectorStore ====================

class MockChromaVectorStore:
    """
    Mock ChromaVectorStore，在内存中存储数据，模拟真实行为
    用于测试 sync 和 index 功能
    """
    
    def __init__(self, collection_name: str = "test_collection"):
        self.collection_name = collection_name
        self._chunks: Dict[str, Dict] = {}  # chunk_id -> chunk_data
        self._embeddings: Dict[str, List[float]] = {}  # chunk_id -> embedding
    
    def add_chunks(self, chunks: List[Dict], embeddings: List[List[float]]) -> None:
        """添加 chunks 和对应的 embeddings"""
        for chunk, emb in zip(chunks, embeddings):
            chunk_id = chunk["id"]
            self._chunks[chunk_id] = {
                "id": chunk_id,
                "text": chunk["text"],
                "metadata": chunk.get("metadata", {})
            }
            self._embeddings[chunk_id] = emb
    
    def get_chunks_with_embeddings(self, chunk_ids: List[str]) -> List[Dict]:
        """获取 chunks 及其 embeddings"""
        results = []
        for cid in chunk_ids:
            if cid in self._chunks:
                chunk = self._chunks[cid].copy()
                chunk["embedding"] = self._embeddings.get(cid)
                chunk["content"] = chunk["text"]  # 兼容字段名
                results.append(chunk)
        return results
    
    def get_all_chunks(self) -> List[Dict]:
        """获取所有 chunks"""
        return [
            {"id": cid, "content": data["text"], "metadata": data["metadata"]}
            for cid, data in self._chunks.items()
        ]
    
    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """删除指定的 chunks"""
        for cid in chunk_ids:
            self._chunks.pop(cid, None)
            self._embeddings.pop(cid, None)
    
    def delete_collection(self) -> None:
        """删除整个 collection"""
        self._chunks.clear()
        self._embeddings.clear()
    
    def get_collection_size(self) -> int:
        """获取 collection 大小"""
        return len(self._chunks)
    
    def search(self, query_embedding: List[float], top_k: int = 5, filters: Dict = None) -> List[Dict]:
        """模拟向量搜索（简单返回前 top_k 个）"""
        results = []
        for cid, data in list(self._chunks.items())[:top_k]:
            results.append({
                "id": cid,
                "text": data["text"],
                "metadata": data["metadata"],
                "score": 0.8  # 模拟相似度分数
            })
        return results
    
    def get_chunk_by_id(self, chunk_id: str) -> Dict:
        """获取单个 chunk"""
        if chunk_id in self._chunks:
            data = self._chunks[chunk_id]
            return {"id": chunk_id, "text": data["text"], "metadata": data["metadata"]}
        return None
    
    def get_legacy_chunk_ids(self, source_file: str = None) -> List[str]:
        """获取旧版本的 chunk IDs"""
        if source_file:
            return [
                cid for cid, data in self._chunks.items()
                if data["metadata"].get("source_file") == source_file
            ]
        return list(self._chunks.keys())
    
    def get_version_stats(self) -> Dict[str, int]:
        """获取版本统计"""
        stats = {}
        for cid, data in self._chunks.items():
            version = data["metadata"].get("strategy_version", "unknown")
            stats[version] = stats.get(version, 0) + 1
        return stats


@pytest.fixture
def mock_chroma_store():
    """创建 Mock ChromaVectorStore"""
    return MockChromaVectorStore()


# ==================== Mock Embedding Model ====================

class MockEmbeddingModel:
    """Mock Embedding 模型，返回固定向量"""
    
    def __init__(self, dim: int = 768):
        self.dim = dim
        self.call_count = 0
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """编码文本，返回固定向量"""
        self.call_count += 1
        return [[0.1] * self.dim for _ in texts]


@pytest.fixture
def mock_embedding_model():
    """创建 Mock Embedding 模型"""
    return MockEmbeddingModel()


# ==================== Mock RAGService ====================

class MockRAGService:
    """Mock RAGService"""
    
    def __init__(self, embedding_model=None, persist_dir=None):
        self.embedding_model = embedding_model or MockEmbeddingModel()
        self.persist_directory = persist_dir or "/tmp/test_chroma"
        self._config = {
            "embedding": {"provider": "mock"},
            "retrieval": {"mode": "vector"}
        }
    
    @classmethod
    def get_instance(cls):
        return cls()
    
    @classmethod
    def reset_instance(cls):
        pass
    
    def get_retriever(self, course_id: str, source: str = "online"):
        return MagicMock()


@pytest.fixture
def mock_rag_service(mock_embedding_model):
    """创建 Mock RAGService"""
    return MockRAGService(embedding_model=mock_embedding_model)


# ==================== Mock Database Session ====================

class MockDBSession:
    """Mock 数据库会话"""
    
    def __init__(self):
        self._data = {}
        self._committed = []
    
    def add(self, obj):
        obj_class = obj.__class__.__name__
        if obj_class not in self._data:
            self._data[obj_class] = []
        self._data[obj_class].append(obj)
    
    def commit(self):
        self._committed.append(True)
    
    def refresh(self, obj):
        pass
    
    def query(self, model):
        return MockQuery(self, model)
    
    def close(self):
        pass


class MockQuery:
    """Mock 查询"""
    
    def __init__(self, session, model):
        self.session = session
        self.model = model
        self._filters = []
    
    def filter(self, *args):
        self._filters.extend(args)
        return self
    
    def first(self):
        # 简单返回 None 或第一个对象
        model_name = self.model.__name__
        if model_name in self.session._data and self.session._data[model_name]:
            return self.session._data[model_name][0]
        return None
    
    def all(self):
        model_name = self.model.__name__
        return self.session._data.get(model_name, [])
    
    def like(self, pattern):
        return self
    
    def in_(self, values):
        return self
    
    def isnot(self, value):
        return self


@pytest.fixture
def mock_db_session():
    """创建 Mock 数据库会话"""
    return MockDBSession()


# ==================== 测试数据 ====================

@pytest.fixture
def sample_chunks():
    """测试用的 chunks 数据"""
    return [
        {
            "id": "chunk_001",
            "text": "大语言模型（LLM）是基于 Transformer 架构的深度学习模型...",
            "metadata": {
                "chapter_id": "course/ch01.md",
                "position": 0,
                "content_type": "paragraph"
            }
        },
        {
            "id": "chunk_002",
            "text": "Transformer 由 Encoder 和 Decoder 组成...",
            "metadata": {
                "chapter_id": "course/ch01.md",
                "position": 1,
                "content_type": "paragraph"
            }
        }
    ]


@pytest.fixture
def sample_embeddings():
    """测试用的 embeddings"""
    return [[0.1] * 768, [0.2] * 768]


@pytest.fixture
def sync_test_data():
    """
    同步测试数据
    
    包含本地 chunks 和 chapter 映射
    """
    local_chunks = [
        {
            "id": "local_1",
            "content": "内容1",
            "metadata": {"chapter_id": "course/ch01.md"},
            "embedding": [0.1] * 768
        },
        {
            "id": "local_2",
            "content": "内容2",
            "metadata": {"chapter_id": "course/ch01.md"},
            "embedding": [0.2] * 768
        },
    ]
    
    chapter_mapping = {
        "course/ch01.md": "uuid-chapter-001"
    }
    
    return {
        "local_chunks": local_chunks,
        "chapter_mapping": chapter_mapping
    }


# ==================== Recall Test Cases ====================

RECALL_TEST_CASES = [
    {
        "query": "什么是大语言模型？",
        "relevant_chunk_ids": ["chunk_001", "chunk_002"],
        "min_recall": 0.8
    },
    {
        "query": "Transformer 的组成部分",
        "relevant_chunk_ids": ["chunk_002"],
        "min_recall": 1.0
    },
]


# ==================== 临时目录 ====================

@pytest.fixture
def temp_chroma_dir():
    """创建临时 ChromaDB 目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
