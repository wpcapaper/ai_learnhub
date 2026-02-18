from typing import List, Dict, Any, Optional
import os
import yaml

from .chunking import (
    SemanticChunkingStrategy,
    ContentFilter,
    Chunk
)
from .embedding import EmbeddingModelFactory, EmbeddingModel
from .vector_store import ChromaVectorStore
from .retrieval import RAGRetriever, RetrievalResult, HybridRetriever
from .multilingual import LanguageDetector, QueryExpander


def _load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 RAG 配置文件
    优先级：指定路径 > 环境变量 > 默认路径
    """
    if config_path is None:
        config_path = os.getenv("RAG_CONFIG_PATH")
    
    if config_path is None:
        # 默认配置路径
        config_path = os.path.join(
            os.path.dirname(__file__),
            "../../config/rag_config.yaml"
        )
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    # 返回默认配置
    return {
        "embedding": {"provider": "openai", "openai": {"model": "text-embedding-3-small"}},
        "vector_store": {"persist_directory": "./data/chroma"},
        "chunking": {"semantic": {"min_chunk_size": 100, "max_chunk_size": 1000, "overlap_size": 200}},
        "retrieval": {"default_top_k": 5},
    }


class RAGService:
    """RAG 服务统一入口，支持配置化加载和延迟初始化"""
    
    _instance: Optional['RAGService'] = None
    _config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> 'RAGService':
        """获取单例实例（延迟初始化）"""
        if cls._instance is None:
            cls._config = _load_config(config_path)
            cls._instance = cls(cls._config)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试或重新加载配置）"""
        cls._instance = None
        cls._config = None
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 RAG 服务
        
        Args:
            config: 配置字典，为 None 时自动加载默认配置
        """
        self._config = config or _load_config()
        
        # 延迟初始化的组件
        self._embedding_model: Optional[EmbeddingModel] = None
        self._query_expander: Optional[QueryExpander] = None
        self._language_detector: Optional[LanguageDetector] = None
        
        # 向量存储配置
        vector_config = self._config.get("vector_store", {})
        self.persist_directory = vector_config.get("persist_directory", "./data/chroma")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 切分策略（立即初始化，无外部依赖）
        chunk_config = self._config.get("chunking", {}).get("semantic", {})
        self.chunking_strategy = SemanticChunkingStrategy(
            min_chunk_size=chunk_config.get("min_chunk_size", 100),
            max_chunk_size=chunk_config.get("max_chunk_size", 1000),
            overlap_size=chunk_config.get("overlap_size", 200),
        )
        
        # 检索配置
        retrieval_config = self._config.get("retrieval", {})
        self.default_top_k = retrieval_config.get("default_top_k", 5)
        self.use_hybrid = False  # 暂不支持混合检索
        self.hybrid_retriever = None
    
    @property
    def embedding_model(self) -> EmbeddingModel:
        """延迟初始化 Embedding 模型"""
        if self._embedding_model is None:
            embedding_config = self._config.get("embedding", {})
            self._embedding_model = EmbeddingModelFactory.create_from_config(embedding_config)
        return self._embedding_model
    
    @property
    def query_expander(self) -> Optional[QueryExpander]:
        """延迟初始化查询扩展器"""
        if self._query_expander is None:
            # 查询扩展默认禁用
            self._query_expander = QueryExpander() if False else None
        return self._query_expander
    
    @property
    def language_detector(self) -> LanguageDetector:
        """延迟初始化语言检测器"""
        if self._language_detector is None:
            self._language_detector = LanguageDetector()
        return self._language_detector
    
    def _get_vector_store(self, course_id: str) -> ChromaVectorStore:
        """获取或创建课程的向量存储"""
        collection_name = f"course_{course_id}"
        return ChromaVectorStore(
            collection_name=collection_name,
            persist_directory=self.persist_directory
        )
    
    def get_retriever(self, course_id: str) -> RAGRetriever:
        """获取或创建检索器"""
        vector_store = self._get_vector_store(course_id)
        return RAGRetriever(
            embedding_model=self.embedding_model,
            vector_store=vector_store
        )
    
    async def index_course_content(
        self,
        content: str,
        course_id: str,
        chapter_id: Optional[str] = None,
        chapter_title: Optional[str] = None,
        clear_existing: bool = False
    ) -> int:
        """
        索引课程内容到向量数据库
        
        Args:
            content: 课程内容（Markdown 格式）
            course_id: 课程 ID
            chapter_id: 章节 ID
            chapter_title: 章节标题
            clear_existing: 是否清除已有索引
        
        Returns:
            索引的 chunk 数量
        """
        # 1. 按语义切分文档
        chunks = self.chunking_strategy.chunk(
            content=content,
            course_id=course_id,
            chapter_id=chapter_id,
            chapter_title=chapter_title
        )
        
        # 2. 过滤不适合 embedding 的内容（如纯代码、公式等）
        filtered_chunks = []
        for chunk in chunks:
            if ContentFilter.should_embed(chunk.text, chunk.metadata.get("content_type", "paragraph")):
                chunk.text = ContentFilter.clean_text(chunk.text)
                if chunk.text:
                    filtered_chunks.append(chunk)
        
        if not filtered_chunks:
            return 0
        
        # 3. 调用 Embedding 服务生成向量
        texts = [chunk.text for chunk in filtered_chunks]
        embeddings = self.embedding_model.encode(texts)
        
        # 4. 准备向量存储数据
        chunk_data = [
            {"id": chunk.chunk_id, "text": chunk.text, "metadata": chunk.metadata}
            for chunk in filtered_chunks
        ]
        
        # 5. 写入向量数据库
        vector_store = self._get_vector_store(course_id)
        if clear_existing:
            vector_store.delete_collection()
            vector_store = self._get_vector_store(course_id)
        
        vector_store.add_chunks(chunk_data, embeddings)
        return len(filtered_chunks)
    
    async def retrieve(
        self,
        query: str,
        course_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
        use_expansion: Optional[bool] = None
    ) -> List[RetrievalResult]:
        """
        检索与查询相关的课程内容
        
        Args:
            query: 用户查询文本
            course_id: 课程 ID
            top_k: 返回结果数量，默认使用配置值
            filters: 元数据过滤条件
            score_threshold: 相似度阈值（低于此值的结果会被过滤）
            use_expansion: 是否启用查询扩展（None 表示使用默认设置）
        
        Returns:
            检索结果列表，按相似度降序排列
        """
        top_k = top_k or self.default_top_k
        
        # 查询扩展（生成多个查询变体以提升召回率）
        queries = [query]
        expander = self.query_expander
        if use_expansion and expander:
            queries = expander.expand(query, max_variants=3)
        
        # 获取检索器并执行检索
        retriever = self.get_retriever(course_id)
        all_results = []
        
        for q in queries:
            results = await retriever.retrieve(
                query=q,
                course_id=course_id,
                top_k=top_k * 2,  # 多检索一些用于后续去重
                filters=filters,
                score_threshold=score_threshold
            )
            all_results.extend(results)
        
        # 按 chunk_id 去重
        seen = set()
        unique_results = []
        for result in all_results:
            if result.chunk_id not in seen:
                seen.add(result.chunk_id)
                unique_results.append(result)
        
        # 按相似度降序排序后返回 Top K
        unique_results.sort(key=lambda x: x.score, reverse=True)
        return unique_results[:top_k]
    
    def get_collection_size(self, course_id: str) -> int:
        """获取课程索引的 chunk 数量"""
        vector_store = self._get_vector_store(course_id)
        return vector_store.get_collection_size()
    
    def delete_course_index(self, course_id: str) -> None:
        """删除课程的向量索引"""
        vector_store = self._get_vector_store(course_id)
        vector_store.delete_collection()
