"""RAG服务层 - 整合所有RAG功能"""

from typing import List, Dict, Any, Optional
import os

from .chunking import (
    SemanticChunkingStrategy,
    ContentFilter,
    Chunk
)
from .embedding import EmbeddingModelFactory, EmbeddingModel
from .vector_store import ChromaVectorStore
from .retrieval import RAGRetriever, RetrievalResult, Reranker, HybridRetriever
from .multilingual import LanguageDetector, QueryExpander


class RAGService:
    """RAG服务 - 统一接口"""
    
    def __init__(
        self,
        embedding_model_key: str = "bge-large-zh",
        persist_directory: Optional[str] = None,
        use_reranker: bool = False,
        use_hybrid: bool = False,
        use_query_expansion: bool = False
    ):
        """
        初始化RAG服务
        
        Args:
            embedding_model_key: Embedding模型键名
            persist_directory: 向量存储持久化目录
            use_reranker: 是否使用重排序
            use_hybrid: 是否使用混合检索
            use_query_expansion: 是否使用查询扩展
        """
        # 初始化Embedding模型
        self.embedding_model = EmbeddingModelFactory.create(embedding_model_key)
        
        # 初始化向量存储
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(__file__),
                "../../../data/chroma"
            )
            os.makedirs(persist_directory, exist_ok=True)
        
        self.persist_directory = persist_directory
        
        # 初始化切割策略
        self.chunking_strategy = SemanticChunkingStrategy(
            min_chunk_size=100,
            max_chunk_size=1000,
            overlap_size=200
        )
        
        # 初始化检索器
        self._init_retriever(use_reranker, use_hybrid)
        
        # 初始化查询扩展器
        self.query_expander = QueryExpander() if use_query_expansion else None
        
        # 语言检测器
        self.language_detector = LanguageDetector()
    
    def _init_retriever(self, use_reranker: bool, use_hybrid: bool):
        """初始化检索器"""
        # 基础向量存储（每个课程一个collection）
        # 这里先不创建，等到需要时再创建
        
        # 基础检索器（延迟初始化）
        self.base_retriever = None
        
        # 重排序器
        self.reranker = Reranker() if use_reranker else None
        
        # 混合检索器
        self.use_hybrid = use_hybrid
        self.hybrid_retriever = None
    
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
        retriever = RAGRetriever(
            embedding_model=self.embedding_model,
            vector_store=vector_store
        )
        return retriever
    
    async def index_course_content(
        self,
        content: str,
        course_id: str,
        chapter_id: Optional[str] = None,
        chapter_title: Optional[str] = None,
        clear_existing: bool = False
    ) -> int:
        """
        索引课程内容
        
        Args:
            content: 课程内容（Markdown格式）
            course_id: 课程ID
            chapter_id: 章节ID
            chapter_title: 章节标题
            clear_existing: 是否清除已有索引
        
        Returns:
            索引的chunk数量
        """
        # 切割文档
        chunks = self.chunking_strategy.chunk(
            content=content,
            course_id=course_id,
            chapter_id=chapter_id,
            chapter_title=chapter_title
        )
        
        # 过滤chunks
        filtered_chunks = []
        for chunk in chunks:
            if ContentFilter.should_embed(chunk.text, chunk.metadata.get("content_type", "paragraph")):
                chunk.text = ContentFilter.clean_text(chunk.text)
                if chunk.text:
                    filtered_chunks.append(chunk)
        
        if not filtered_chunks:
            return 0
        
        # 生成embeddings
        texts = [chunk.text for chunk in filtered_chunks]
        embeddings = self.embedding_model.encode(texts)
        
        # 准备数据
        chunk_data = [
            {
                "id": chunk.chunk_id,
                "text": chunk.text,
                "metadata": chunk.metadata
            }
            for chunk in filtered_chunks
        ]
        
        # 获取向量存储
        vector_store = self._get_vector_store(course_id)
        
        # 清除已有索引
        if clear_existing:
            vector_store.delete_collection()
            vector_store = self._get_vector_store(course_id)
        
        # 添加到向量存储
        vector_store.add_chunks(chunk_data, embeddings)
        
        return len(filtered_chunks)
    
    async def retrieve(
        self,
        query: str,
        course_id: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
        use_expansion: Optional[bool] = None
    ) -> List[RetrievalResult]:
        """
        检索相关内容
        
        Args:
            query: 查询文本
            course_id: 课程ID
            top_k: 返回Top K结果
            filters: 元数据过滤条件
            score_threshold: 相似度阈值
            use_expansion: 是否使用查询扩展（None表示使用默认设置）
        
        Returns:
            检索结果列表
        """
        # 查询扩展
        queries = [query]
        if (use_expansion or (use_expansion is None and self.query_expander)):
            queries = self.query_expander.expand(query, max_variants=3)
        
        # 获取检索器
        if self.use_hybrid:
            retriever = self._get_hybrid_retriever(course_id)
        else:
            retriever = self.get_retriever(course_id)
        
        # 执行检索（使用第一个查询，或合并多个查询的结果）
        all_results = []
        for q in queries:
            results = await retriever.retrieve(
                query=q,
                course_id=course_id,
                top_k=top_k * 2,  # 多检索一些用于去重和重排序
                filters=filters,
                score_threshold=score_threshold
            )
            all_results.extend(results)
        
        # 去重（按chunk_id）
        seen = set()
        unique_results = []
        for result in all_results:
            if result.chunk_id not in seen:
                seen.add(result.chunk_id)
                unique_results.append(result)
        
        # 重排序（如果启用）
        if self.reranker and unique_results:
            unique_results = self.reranker.rerank(query, unique_results, top_k)
        
        # 返回Top K
        return unique_results[:top_k]
    
    def _get_hybrid_retriever(self, course_id: str) -> HybridRetriever:
        """获取混合检索器"""
        if self.hybrid_retriever is None:
            base_retriever = self.get_retriever(course_id)
            # TODO: 初始化关键词检索器（需要chunks数据）
            self.hybrid_retriever = HybridRetriever(
                vector_retriever=base_retriever,
                keyword_retriever=None
            )
        return self.hybrid_retriever
    
    def get_collection_size(self, course_id: str) -> int:
        """获取课程索引的chunk数量"""
        vector_store = self._get_vector_store(course_id)
        return vector_store.get_collection_size()
    
    def delete_course_index(self, course_id: str) -> None:
        """删除课程索引"""
        vector_store = self._get_vector_store(course_id)
        vector_store.delete_collection()
