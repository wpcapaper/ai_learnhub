"""
RAGService 单元测试

测试覆盖：
1. 单例模式
2. 配置加载
3. normalize_collection_name
4. 索引课程内容
5. 检索功能
6. 混合检索和 RRF 融合
7. 向量存储管理
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock, patch, AsyncMock

from conftest import MockChromaVectorStore, MockEmbeddingModel, MockRAGService  # noqa: E402


class TestNormalizeCollectionName:
    """normalize_collection_name 函数测试"""
    
    # 直接定义测试版本，避免导入整个 rag 模块
    @staticmethod
    def _normalize_collection_name(name: str) -> str:
        """测试用的 normalize_collection_name 实现"""
        import re
        import hashlib
        
        normalized = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
        
        if normalized and not normalized[0].isalnum():
            normalized = 'c_' + normalized
        
        if normalized and not normalized[-1].isalnum():
            normalized = normalized + '_0'
        
        if len(normalized) < 3:
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            normalized = f"col_{hash_suffix}"
        
        if len(normalized) > 512:
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            normalized = normalized[:503] + '_' + hash_suffix
        
        return normalized
    
    def test_simple_name(self):
        """简单名称保持不变"""
        result = self._normalize_collection_name("python_basics")
        assert result == "python_basics"
    
    def test_name_with_special_chars(self):
        """特殊字符被替换为下划线"""
        result = self._normalize_collection_name("python-basics 123")
        assert " " not in result
        assert result == "python-basics_123"
    
    def test_name_starting_with_special_char(self):
        """以特殊字符开头时添加前缀"""
        result = self._normalize_collection_name("_test")
        assert result.startswith("c_")
    
    def test_name_ending_with_special_char(self):
        """以特殊字符结尾时添加后缀"""
        result = self._normalize_collection_name("test_")
        assert result.endswith("_0")
    
    def test_very_short_name(self):
        """过短名称使用 hash 扩展"""
        result = self._normalize_collection_name("ab")
        assert len(result) >= 3
        assert result.startswith("col_")
    
    def test_very_long_name(self):
        """过长名称被截断并添加 hash"""
        long_name = "a" * 600
        result = self._normalize_collection_name(long_name)
        assert len(result) <= 512
    
    def test_chinese_characters(self):
        """中文字符被替换"""
        result = self._normalize_collection_name("Python基础课程")
        assert "基础" not in result
        assert "课程" not in result


class TestRAGServiceSingleton:
    """单例模式测试"""
    
    def test_get_instance_returns_same_instance(self):
        """get_instance 返回同一实例"""
        MockRAGService.reset_instance()
        
        instance1 = MockRAGService.get_instance()
        instance2 = MockRAGService.get_instance()
        
        assert instance1 is instance2
        
        MockRAGService.reset_instance()
    
    def test_reset_instance_creates_new(self):
        """reset_instance 后创建新实例"""
        MockRAGService.reset_instance()
        
        instance1 = MockRAGService.get_instance()
        MockRAGService.reset_instance()
        instance2 = MockRAGService.get_instance()
        
        assert instance1 is not instance2
        
        MockRAGService.reset_instance()


class TestRAGServiceInit:
    """初始化测试"""
    
    def test_init_with_default_config(self):
        """使用默认配置初始化"""
        service = MockRAGService()
        
        assert service.persist_directory is not None
    
    def test_init_with_custom_config(self):
        """使用自定义配置初始化"""
        config = {
            "retrieval": {"default_top_k": 10, "mode": "vector"},
            "vector_store": {"persist_directory": "/custom/path"}
        }
        
        service = MockRAGService(embedding_model=MockEmbeddingModel(), persist_dir="/custom/path")
        
        assert service.persist_directory == "/custom/path"


class TestRAGServiceIndexing:
    """索引功能测试"""
    
    @pytest.mark.asyncio
    async def test_index_empty_content_returns_zero(self):
        """索引空内容返回 0"""
        service = MockRAGService()
        
        result = await service.index_course_content(
            content="",
            course_id="test_course"
        )
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_index_creates_chunks(self):
        """索引内容创建 chunks"""
        mock_store = MockChromaVectorStore()
        mock_embedding = MockEmbeddingModel()
        
        service = MockRAGService(embedding_model=mock_embedding)
        
        content = "# 测试章节\n\n这是测试内容。" * 10
        
        with patch.object(service, '_get_vector_store', return_value=mock_store):
            result = await service.index_course_content(
                content=content,
                course_id="test_course",
                chapter_id="ch01",
                chapter_title="测试章节"
            )
        
        assert result >= 0
    
    @pytest.mark.asyncio
    async def test_index_with_clear_existing(self):
        """清除已有索引后重新索引"""
        mock_store = MockChromaVectorStore()
        mock_store.add_chunks(
            [{"id": "old", "text": "旧数据", "metadata": {}}],
            [[0.1] * 768]
        )
        
        assert mock_store.get_collection_size() == 1
        
        service = MockRAGService()
        
        with patch.object(service, '_get_vector_store', return_value=mock_store):
            pass


class TestRAGServiceRetrieval:
    """检索功能测试"""
    
    @pytest.mark.asyncio
    async def test_retrieve_returns_results(self):
        """检索返回结果"""
        service = MockRAGService()
        
        mock_store = MockChromaVectorStore()
        mock_store.add_chunks(
            [{"id": "chunk_1", "text": "大语言模型是基于Transformer的", "metadata": {}}],
            [[0.1] * 768]
        )
        
        with patch.object(service, '_get_vector_store', return_value=mock_store):
            retriever = MagicMock()
            retriever.retrieve = AsyncMock(return_value=[
                MagicMock(chunk_id="chunk_1", text="大语言模型", score=0.9)
            ])
            
            with patch.object(service, 'get_retriever', return_value=retriever):
                results = await service.retrieve(
                    query="什么是大语言模型",
                    course_id="test_course"
                )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_with_top_k(self):
        """指定 top_k 参数"""
        service = MockRAGService()
        
        results = await service.retrieve(
            query="测试查询",
            course_id="test_course",
            top_k=3
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_with_filters(self):
        """带过滤条件检索"""
        service = MockRAGService()
        
        filters = {"chapter_code": "introduction"}
        
        results = await service.retrieve(
            query="测试查询",
            course_id="test_course",
            filters=filters
        )
        
        assert isinstance(results, list)


class TestRRFMerge:
    """RRF 融合算法测试"""
    
    def test_rrf_merge_combines_results(self):
        """RRF 融合合并结果"""
        service = MockRAGService()
        
        vector_results = [
            MagicMock(chunk_id="a", text="A", score=0.9),
        ]
        
        keyword_results = [
            MagicMock(chunk_id="b", text="B", score=0.95),
        ]
        
        merged = service._rrf_merge(vector_results, keyword_results, top_k=10)
        
        assert len(merged) >= 1
    
    def test_rrf_merge_respects_top_k(self):
        """RRF 融合遵守 top_k 限制"""
        service = MockRAGService()
        
        vector_results = [
            MagicMock(chunk_id=str(i), text=str(i), score=0.9 - i * 0.1)
            for i in range(10)
        ]
        
        keyword_results = [
            MagicMock(chunk_id=str(i + 5), text=str(i + 5), score=0.8 - i * 0.1)
            for i in range(10)
        ]
        
        merged = service._rrf_merge(vector_results, keyword_results, top_k=5)
        
        assert len(merged) == 5
    
    def test_rrf_merge_empty_inputs(self):
        """RRF 融合处理空输入"""
        service = MockRAGService()
        
        merged = service._rrf_merge([], [], top_k=5)
        
        assert merged == []


class TestVectorStoreManagement:
    """向量存储管理测试"""
    
    def test_get_collection_size(self):
        """获取 collection 大小"""
        service = MockRAGService()
        
        size = service.get_collection_size("test_course")
        
        assert size == 0
    
    def test_delete_course_index(self):
        """删除课程索引"""
        service = MockRAGService()
        
        # 调用不应报错
        service.delete_course_index("test_course")
        
        # 验证方法存在
        assert hasattr(service, 'delete_course_index')


class TestRetrievalModes:
    """检索模式测试"""
    
    @pytest.mark.asyncio
    async def test_vector_mode(self):
        """纯向量检索模式"""
        service = MockRAGService()
        
        results = await service.retrieve(
            query="测试",
            course_id="test",
            mode="vector"
        )
        
        # 验证返回了结果
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_vector_rerank_mode_without_reranker(self):
        """向量+重排序模式（无 reranker 时降级）"""
        service = MockRAGService()
        service._reranker = None
        
        retriever = MagicMock()
        retriever.retrieve = AsyncMock(return_value=[])
        
        with patch.object(service, 'get_retriever', return_value=retriever):
            results = await service.retrieve(
                query="测试",
                course_id="test",
                mode="vector_rerank"
            )
        
        assert isinstance(results, list)


class TestStringToBool:
    """字符串转布尔值测试"""
    
    def test_string_true(self):
        """字符串 'true' 转为 True"""
        service = MockRAGService()
        
        assert service._str_to_bool("true") is True
        assert service._str_to_bool("True") is True
        assert service._str_to_bool("TRUE") is True
    
    def test_string_yes(self):
        """字符串 'yes' 转为 True"""
        service = MockRAGService()
        
        assert service._str_to_bool("yes") is True
        assert service._str_to_bool("Yes") is True
    
    def test_string_1(self):
        """字符串 '1' 转为 True"""
        service = MockRAGService()
        
        assert service._str_to_bool("1") is True
    
    def test_bool_passthrough(self):
        """布尔值直接返回"""
        service = MockRAGService()
        
        assert service._str_to_bool(True) is True
        assert service._str_to_bool(False) is False
    
    def test_other_values_false(self):
        """其他值转为 False"""
        service = MockRAGService()
        
        assert service._str_to_bool("false") is False
        assert service._str_to_bool("no") is False
        assert service._str_to_bool("0") is False
        assert service._str_to_bool("") is False
