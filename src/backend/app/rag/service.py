from typing import List, Dict, Any, Optional
import os
import re
import yaml
import logging

from .chunking import (
    SemanticChunkingStrategy,
    ContentFilter,
    Chunk
)
from .embedding import EmbeddingModelFactory, EmbeddingModel
from .vector_store import ChromaVectorStore
from .retrieval import RAGRetriever, RetrievalResult, HybridRetriever, Reranker
from .multilingual import LanguageDetector, QueryExpander

logger = logging.getLogger(__name__)


def normalize_collection_name(name: str) -> str:
    """
    将任意字符串转换为合法的 ChromaDB collection 名称
    ChromaDB 要求: 3-512字符，只允许 [a-zA-Z0-9._-]，必须以字母或数字开头和结尾
    """
    import hashlib
    
    # 移除或替换非法字符
    normalized = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    
    # 确保以字母或数字开头
    if normalized and not normalized[0].isalnum():
        normalized = 'c_' + normalized
    
    # 确保以字母或数字结尾
    if normalized and not normalized[-1].isalnum():
        normalized = normalized + '_0'
    
    # 如果规范化后太短或为空，使用 hash
    if len(normalized) < 3:
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        normalized = f"col_{hash_suffix}"
    
    # 限制长度
    if len(normalized) > 512:
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        normalized = normalized[:503] + '_' + hash_suffix
    
    return normalized


class RetrievalMode:
    """检索模式枚举"""
    VECTOR = "vector"          # 纯向量检索
    KEYWORD = "keyword"        # 纯关键词检索
    HYBRID = "hybrid"          # 混合检索（向量+关键词）
    VECTOR_RERANK = "vector_rerank"  # 向量+重排序


def _resolve_env_vars(value: Any) -> Any:
    """
    递归解析配置中的环境变量
    支持 ${VAR_NAME:default} 语法
    """
    if isinstance(value, str):
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default_value)
        
        return re.sub(pattern, replace_env_var, value)
    
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    
    return value


def _load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 RAG 配置文件
    优先级：指定路径 > 环境变量 > 默认路径
    """
    if config_path is None:
        config_path = os.getenv("RAG_CONFIG_PATH")
    
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__),
            "../../config/rag_config.yaml"
        )
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}
            return _resolve_env_vars(raw_config)
    
    return {
        "embedding": {"provider": "openai", "openai": {"model": "text-embedding-3-small"}},
        "vector_store": {"persist_directory": "./data/chroma"},
        "chunking": {"semantic": {"min_chunk_size": 100, "max_chunk_size": 1000, "overlap_size": 200}},
        "retrieval": {"default_top_k": 5},
    }


class RAGService:
    """RAG 服务统一入口，支持配置化加载和延迟初始化"""
    
    _instance: Optional['RAGService'] = None
    _class_config: Optional[Dict[str, Any]] = None  # 类变量，单例模式使用
    
    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> 'RAGService':
        """获取单例实例（延迟初始化）"""
        if cls._instance is None:
            cls._class_config = _load_config(config_path)
            cls._instance = cls(cls._class_config)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试或重新加载配置）"""
        cls._instance = None
        cls._class_config = None
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 RAG 服务
        
        Args:
            config: 配置字典，为 None 时自动加载默认配置
        """
        if config is not None:
            self._config = config
        else:
            self._config = _load_config()
        
        # 延迟初始化的组件
        self._embedding_model: Optional[EmbeddingModel] = None
        self._reranker: Optional[Reranker] = None
        self._query_expander: Optional[QueryExpander] = None
        self._language_detector: Optional[LanguageDetector] = None
        self._keyword_retriever: Optional[Any] = None  # 关键词检索器（混合检索用）
        
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
        
        # 检索模式: vector | hybrid | vector_rerank
        # 默认使用纯向量检索，最简单
        self.retrieval_mode = retrieval_config.get("mode", RetrievalMode.VECTOR)
        
        # 混合检索权重（仅hybrid模式使用）
        self.vector_weight = retrieval_config.get("vector_weight", 0.7)
        self.keyword_weight = retrieval_config.get("keyword_weight", 0.3)
    
    @property
    def embedding_model(self) -> EmbeddingModel:
        """延迟初始化 Embedding 模型"""
        if self._embedding_model is None:
            embedding_config = self._config.get("embedding", {})
            self._embedding_model = EmbeddingModelFactory.create_from_config(embedding_config)
        return self._embedding_model
    
    @property
    def reranker(self) -> Optional[Reranker]:
        """延迟初始化 Reranker（仅配置启用时创建）"""
        if self._reranker is None:
            rerank_config = self._config.get("rerank", {})
            enabled = self._str_to_bool(rerank_config.get("enabled", "false"))
            
            if enabled:
                provider = rerank_config.get("provider", "local")
                if provider == "local":
                    local_config = rerank_config.get("local", {})
                    endpoint = local_config.get("endpoint", "")
                    if endpoint:
                        self._reranker = Reranker(
                            endpoint=endpoint,
                            timeout=local_config.get("timeout", 30)
                        )
                        logger.info(f"Reranker已启用: {endpoint}")
                elif provider == "cohere":
                    cohere_config = rerank_config.get("cohere", {})
                    api_key = cohere_config.get("api_key", "")
                    if api_key:
                        self._reranker = Reranker(
                            endpoint="https://api.cohere.ai/v1/rerank",
                            api_key=api_key,
                            timeout=30
                        )
                        logger.info("Reranker已启用: Cohere API")
        
        return self._reranker
    
    def _str_to_bool(self, value: Any) -> bool:
        """字符串转布尔值"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    
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
        collection_name = normalize_collection_name(f"course_{course_id}")
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
        source_file: Optional[str] = None,
        clear_existing: bool = False
    ) -> int:
        """
        索引课程内容到向量数据库
        
        Args:
            content: 课程内容（Markdown 格式）
            course_id: 课程 ID
            chapter_id: 章节 ID
            chapter_title: 章节标题
            source_file: 源文件路径（用于跨设备复用）
            clear_existing: 是否清除已有索引
        
        Returns:
            索引的 chunk 数量
        """
        # 1. 按语义切分文档
        chunks = self.chunking_strategy.chunk(
            content=content,
            course_id=course_id,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            source_file=source_file or chapter_title
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
        use_expansion: Optional[bool] = None,
        mode: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        检索与查询相关的课程内容
        
        Args:
            query: 用户查询文本
            course_id: 课程 ID
            top_k: 返回结果数量，默认使用配置值
            filters: 元数据过滤条件
            score_threshold: 相似度阈值
            use_expansion: 是否启用查询扩展
            mode: 检索模式，覆盖配置值
        
        Returns:
            检索结果列表，按相似度降序排列
        """
        # 确保 top_k 非空
        actual_top_k = top_k if top_k is not None else self.default_top_k
        retrieval_mode = mode or self.retrieval_mode
        
        # 获取基础检索器
        retriever = self.get_retriever(course_id)
        
        # 根据模式执行检索
        if retrieval_mode == RetrievalMode.VECTOR:
            results = await self._vector_retrieve(retriever, query, actual_top_k, filters, score_threshold)
        
        elif retrieval_mode == RetrievalMode.VECTOR_RERANK:
            results = await self._vector_rerank_retrieve(retriever, query, actual_top_k, filters, score_threshold)
        
        elif retrieval_mode == RetrievalMode.HYBRID:
            results = await self._hybrid_retrieve(retriever, query, course_id, actual_top_k, filters, score_threshold)
        
        else:
            results = await self._vector_retrieve(retriever, query, actual_top_k, filters, score_threshold)
        
        return results
    
    async def _vector_retrieve(
        self,
        retriever: RAGRetriever,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        score_threshold: float
    ) -> List[RetrievalResult]:
        """纯向量检索"""
        results = await retriever.retrieve(
            query=query,
            course_id="",
            top_k=top_k,
            filters=filters,
            score_threshold=score_threshold
        )
        return results
    
    async def _vector_rerank_retrieve(
        self,
        retriever: RAGRetriever,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        score_threshold: float
    ) -> List[RetrievalResult]:
        """向量检索 + Rerank重排序"""
        reranker = self.reranker
        
        if reranker is None:
            logger.debug("Rerank未配置，降级为纯向量检索")
            return await self._vector_retrieve(retriever, query, top_k, filters, score_threshold)
        
        candidates = await retriever.retrieve(
            query=query,
            course_id="",
            top_k=top_k * 3,
            filters=filters,
            score_threshold=score_threshold
        )
        
        if not candidates:
            return []
        
        reranked = reranker.rerank(query, candidates, top_k)
        return reranked
    
    async def _hybrid_retrieve(
        self,
        retriever: RAGRetriever,
        query: str,
        course_id: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        score_threshold: float
    ) -> List[RetrievalResult]:
        """混合检索（向量+关键词）"""
        vector_results = await retriever.retrieve(
            query=query,
            course_id="",
            top_k=top_k * 2,
            filters=filters,
            score_threshold=score_threshold
        )
        
        if not hasattr(self, '_keyword_retriever') or self._keyword_retriever is None:
            logger.debug("关键词检索器未配置，降级为纯向量检索")
            return vector_results[:top_k]
        
        keyword_results = await self._keyword_retriever.retrieve(
            query=query,
            course_id=course_id,
            top_k=top_k * 2,
            filters=filters
        )
        
        merged = self._rrf_merge(vector_results, keyword_results, top_k)
        return merged
    
    def _rrf_merge(
        self,
        vector_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult],
        top_k: int,
        k: int = 60
    ) -> List[RetrievalResult]:
        """Reciprocal Rank Fusion 融合"""
        scores: Dict[str, float] = {}
        result_map: Dict[str, RetrievalResult] = {}
        
        for rank, result in enumerate(vector_results):
            rrf_score = self.vector_weight / (k + rank + 1)
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + rrf_score
            result_map[result.chunk_id] = result
        
        for rank, result in enumerate(keyword_results):
            rrf_score = self.keyword_weight / (k + rank + 1)
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + rrf_score
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result
        
        for chunk_id, score in scores.items():
            result_map[chunk_id].score = score
        
        sorted_results = sorted(
            result_map.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def get_collection_size(self, course_id: str) -> int:
        """获取课程索引的 chunk 数量"""
        vector_store = self._get_vector_store(course_id)
        return vector_store.get_collection_size()
    
    def delete_course_index(self, course_id: str) -> None:
        """删除课程的向量索引"""
        vector_store = self._get_vector_store(course_id)
        vector_store.delete_collection()
