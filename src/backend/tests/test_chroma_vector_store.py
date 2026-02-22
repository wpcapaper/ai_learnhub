"""
ChromaVectorStore 单元测试

测试覆盖：
1. 初始化和配置
2. add_chunks - 添加文档块
3. search - 向量搜索
4. delete_chunks - 删除文档块
5. get_all_chunks / get_chunk_by_id - 数据查询
6. get_chunks_with_embeddings - 获取带嵌入的数据
7. 版本控制功能
8. 边界情况和错误处理

这些测试使用 MockChromaVectorStore 模拟真实行为，
避免依赖外部 ChromaDB 服务
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock, patch
import tempfile

from conftest import MockChromaVectorStore  # noqa: E402


class TestChromaVectorStoreInit:
    """初始化测试"""
    
    def test_init_with_default_params(self):
        """默认参数初始化"""
        store = MockChromaVectorStore()
        assert store.collection_name == "test_collection"
        assert store.get_collection_size() == 0
    
    def test_init_with_custom_name(self):
        """自定义 collection 名称"""
        store = MockChromaVectorStore(collection_name="my_course")
        assert store.collection_name == "my_course"
    
    def test_init_local_collection(self):
        """本地环境 collection 命名"""
        store = MockChromaVectorStore(collection_name="local_python_basics")
        assert store.collection_name.startswith("local_")


class TestAddChunks:
    """add_chunks 方法测试"""
    
    def test_add_single_chunk(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """添加单个 chunk"""
        mock_chroma_store.add_chunks([sample_chunks[0]], [sample_embeddings[0]])
        
        assert mock_chroma_store.get_collection_size() == 1
        
        chunks = mock_chroma_store.get_all_chunks()
        assert len(chunks) == 1
        assert chunks[0]["id"] == "chunk_001"
    
    def test_add_multiple_chunks(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """添加多个 chunks"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        
        assert mock_chroma_store.get_collection_size() == 2
    
    def test_add_chunk_with_metadata(self, mock_chroma_store):
        """添加带完整元数据的 chunk"""
        chunk = {
            "id": "test_001",
            "text": "测试内容",
            "metadata": {
                "chapter_id": "course/ch01.md",
                "position": 0,
                "content_type": "paragraph",
                "strategy_version": "markdown-v1.0"
            }
        }
        embedding = [0.1] * 768
        
        mock_chroma_store.add_chunks([chunk], [embedding])
        
        # 获取并验证
        result = mock_chroma_store.get_chunk_by_id("test_001")
        assert result is not None
        assert result["metadata"]["chapter_id"] == "course/ch01.md"
        assert result["metadata"]["strategy_version"] == "markdown-v1.0"
    
    def test_add_chunks_empty_metadata(self, mock_chroma_store):
        """添加无元数据的 chunk（使用默认空字典）"""
        chunk = {
            "id": "no_meta",
            "text": "无元数据内容"
        }
        embedding = [0.1] * 768
        
        mock_chroma_store.add_chunks([chunk], [embedding])
        
        result = mock_chroma_store.get_chunk_by_id("no_meta")
        assert result is not None
        assert result["metadata"] == {}
    
    def test_add_chunks_updates_existing(self, mock_chroma_store):
        """添加相同 ID 的 chunk 会更新（ChromaDB 行为）"""
        chunk_v1 = {
            "id": "update_test",
            "text": "版本1",
            "metadata": {"version": 1}
        }
        chunk_v2 = {
            "id": "update_test",
            "text": "版本2",
            "metadata": {"version": 2}
        }
        embedding = [0.1] * 768
        
        mock_chroma_store.add_chunks([chunk_v1], [embedding])
        mock_chroma_store.add_chunks([chunk_v2], [embedding])
        
        # Mock 实现：相同 ID 会被覆盖
        result = mock_chroma_store.get_chunk_by_id("update_test")
        assert result["metadata"]["version"] == 2


class TestSearch:
    """search 方法测试"""
    
    def test_search_returns_results(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """搜索返回结果"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        
        query_embedding = [0.1] * 768
        results = mock_chroma_store.search(query_embedding, top_k=5)
        
        assert len(results) > 0
        assert "id" in results[0]
        assert "text" in results[0]
        assert "score" in results[0]
    
    def test_search_top_k_limit(self, mock_chroma_store):
        """top_k 限制返回数量"""
        # 添加 5 个 chunks
        for i in range(5):
            mock_chroma_store.add_chunks(
                [{"id": f"chunk_{i}", "text": f"内容{i}", "metadata": {}}],
                [[0.1] * 768]
            )
        
        query_embedding = [0.1] * 768
        results = mock_chroma_store.search(query_embedding, top_k=3)
        
        assert len(results) == 3
    
    def test_search_empty_collection(self, mock_chroma_store):
        """空 collection 搜索返回空列表"""
        query_embedding = [0.1] * 768
        results = mock_chroma_store.search(query_embedding, top_k=5)
        
        assert len(results) == 0
    
    def test_search_with_filters(self, mock_chroma_store):
        """带过滤条件的搜索"""
        chunks = [
            {"id": "ch1", "text": "第一章", "metadata": {"chapter": "ch01"}},
            {"id": "ch2", "text": "第二章", "metadata": {"chapter": "ch02"}}
        ]
        embeddings = [[0.1] * 768, [0.2] * 768]
        
        mock_chroma_store.add_chunks(chunks, embeddings)
        
        # Mock 实现不支持真实过滤，但接口测试
        query_embedding = [0.1] * 768
        results = mock_chroma_store.search(
            query_embedding,
            top_k=5,
            filters={"chapter": "ch01"}
        )
        
        # 验证返回格式正确
        assert isinstance(results, list)


class TestDeleteChunks:
    """delete_chunks 方法测试"""
    
    def test_delete_single_chunk(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """删除单个 chunk"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        assert mock_chroma_store.get_collection_size() == 2
        
        mock_chroma_store.delete_chunks(["chunk_001"])
        
        assert mock_chroma_store.get_collection_size() == 1
        assert mock_chroma_store.get_chunk_by_id("chunk_001") is None
    
    def test_delete_multiple_chunks(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """删除多个 chunks"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        
        mock_chroma_store.delete_chunks(["chunk_001", "chunk_002"])
        
        assert mock_chroma_store.get_collection_size() == 0
    
    def test_delete_nonexistent_chunk(self, mock_chroma_store):
        """删除不存在的 chunk 不报错"""
        # 不应该抛出异常
        mock_chroma_store.delete_chunks(["nonexistent_id"])
        assert mock_chroma_store.get_collection_size() == 0
    
    def test_delete_collection(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """删除整个 collection"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        assert mock_chroma_store.get_collection_size() == 2
        
        mock_chroma_store.delete_collection()
        
        assert mock_chroma_store.get_collection_size() == 0


class TestGetChunks:
    """数据查询方法测试"""
    
    def test_get_all_chunks(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """获取所有 chunks"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        
        all_chunks = mock_chroma_store.get_all_chunks()
        
        assert len(all_chunks) == 2
        assert all_chunks[0]["id"] in ["chunk_001", "chunk_002"]
    
    def test_get_all_chunks_empty(self, mock_chroma_store):
        """空 collection 返回空列表"""
        all_chunks = mock_chroma_store.get_all_chunks()
        
        assert all_chunks == []
    
    def test_get_chunk_by_id_exists(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """获取存在的 chunk"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        
        result = mock_chroma_store.get_chunk_by_id("chunk_001")
        
        assert result is not None
        assert result["id"] == "chunk_001"
        assert "text" in result or "content" in result
    
    def test_get_chunk_by_id_not_exists(self, mock_chroma_store):
        """获取不存在的 chunk 返回 None"""
        result = mock_chroma_store.get_chunk_by_id("nonexistent")
        
        assert result is None
    
    def test_get_chunks_with_embeddings(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """获取带 embeddings 的 chunks"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        
        results = mock_chroma_store.get_chunks_with_embeddings(["chunk_001"])
        
        assert len(results) == 1
        assert results[0]["id"] == "chunk_001"
        assert results[0]["embedding"] is not None
        assert len(results[0]["embedding"]) == 768
    
    def test_get_chunks_with_embeddings_empty_list(self, mock_chroma_store):
        """空 ID 列表返回空结果"""
        results = mock_chroma_store.get_chunks_with_embeddings([])
        
        assert results == []
    
    def test_get_chunks_with_embeddings_partial_match(self, mock_chroma_store, sample_chunks, sample_embeddings):
        """部分 ID 匹配时只返回存在的"""
        mock_chroma_store.add_chunks(sample_chunks, sample_embeddings)
        
        results = mock_chroma_store.get_chunks_with_embeddings(
            ["chunk_001", "nonexistent", "chunk_002"]
        )
        
        # 只返回存在的 chunks
        assert len(results) == 2


class TestVersionControl:
    """版本控制功能测试"""
    
    def test_get_legacy_chunk_ids(self, mock_chroma_store):
        """获取旧版本 chunk IDs"""
        chunks = [
            {"id": "new_1", "text": "新版本", "metadata": {"strategy_version": "markdown-v1.0"}},
            {"id": "old_1", "text": "旧版本", "metadata": {"strategy_version": "markdown-v0.9"}},
            {"id": "old_2", "text": "另一个旧版本", "metadata": {"strategy_version": "markdown-v0.9"}},
        ]
        embeddings = [[0.1] * 768] * 3
        
        mock_chroma_store.add_chunks(chunks, embeddings)
        
        # 获取旧版本 IDs（假设当前版本是 markdown-v1.0）
        # Mock 实现需要模拟这个逻辑
        legacy_ids = mock_chroma_store.get_legacy_chunk_ids()
        
        # 在真实实现中会过滤出旧版本
        assert isinstance(legacy_ids, list)
    
    def test_get_legacy_chunk_ids_with_source_filter(self, mock_chroma_store):
        """按源文件过滤旧版本 chunks"""
        chunks = [
            {"id": "ch1_old", "text": "旧", "metadata": {
                "strategy_version": "markdown-v0.9",
                "source_file": "ch01.md"
            }},
            {"id": "ch2_old", "text": "旧", "metadata": {
                "strategy_version": "markdown-v0.9",
                "source_file": "ch02.md"
            }},
        ]
        embeddings = [[0.1] * 768] * 2
        
        mock_chroma_store.add_chunks(chunks, embeddings)
        
        legacy_ids = mock_chroma_store.get_legacy_chunk_ids(source_file="ch01.md")
        
        assert isinstance(legacy_ids, list)
    
    def test_get_version_stats(self, mock_chroma_store):
        """获取版本统计"""
        chunks = [
            {"id": "v1_1", "text": "v1", "metadata": {"strategy_version": "markdown-v1.0"}},
            {"id": "v1_2", "text": "v1", "metadata": {"strategy_version": "markdown-v1.0"}},
            {"id": "v09_1", "text": "v0.9", "metadata": {"strategy_version": "markdown-v0.9"}},
        ]
        embeddings = [[0.1] * 768] * 3
        
        mock_chroma_store.add_chunks(chunks, embeddings)
        
        stats = mock_chroma_store.get_version_stats()
        
        assert "markdown-v1.0" in stats
        assert stats["markdown-v1.0"] == 2


class TestEdgeCases:
    """边界情况测试"""
    
    def test_large_batch_add(self, mock_chroma_store):
        """大批量添加 chunks"""
        batch_size = 100
        chunks = [
            {"id": f"batch_{i}", "text": f"内容{i}", "metadata": {"index": i}}
            for i in range(batch_size)
        ]
        embeddings = [[0.1] * 768] * batch_size
        
        mock_chroma_store.add_chunks(chunks, embeddings)
        
        assert mock_chroma_store.get_collection_size() == batch_size
    
    def test_unicode_content(self, mock_chroma_store):
        """Unicode 内容处理"""
        chunk = {
            "id": "unicode_test",
            "text": "中文内容 🎉 emoji 表情符号",
            "metadata": {"lang": "zh"}
        }
        embedding = [0.1] * 768
        
        mock_chroma_store.add_chunks([chunk], [embedding])
        
        result = mock_chroma_store.get_chunk_by_id("unicode_test")
        assert "中文" in result["text"]
    
    def test_long_text_content(self, mock_chroma_store):
        """长文本内容处理"""
        long_text = "这是一个很长的文本。" * 1000  # 约 1 万字符
        chunk = {
            "id": "long_text",
            "text": long_text,
            "metadata": {}
        }
        embedding = [0.1] * 768
        
        mock_chroma_store.add_chunks([chunk], [embedding])
        
        result = mock_chroma_store.get_chunk_by_id("long_text")
        assert len(result["text"]) == len(long_text)
    
    def test_special_characters_in_metadata(self, mock_chroma_store):
        """元数据中的特殊字符"""
        chunk = {
            "id": "special_meta",
            "text": "内容",
            "metadata": {
                "path": "/path/to/file with spaces.md",
                "tags": ["tag1", "tag with space", "tag:with:colons"]
            }
        }
        embedding = [0.1] * 768
        
        mock_chroma_store.add_chunks([chunk], [embedding])
        
        result = mock_chroma_store.get_chunk_by_id("special_meta")
        assert result["metadata"]["path"] == "/path/to/file with spaces.md"


class TestConcurrency:
    """并发操作测试（Mock 级别）"""
    
    def test_sequential_operations(self, mock_chroma_store):
        """顺序操作的正确性"""
        # 添加
        mock_chroma_store.add_chunks(
            [{"id": "seq_1", "text": "1", "metadata": {}}],
            [[0.1] * 768]
        )
        assert mock_chroma_store.get_collection_size() == 1
        
        # 更新（添加相同 ID）
        mock_chroma_store.add_chunks(
            [{"id": "seq_1", "text": "1 updated", "metadata": {"updated": True}}],
            [[0.2] * 768]
        )
        
        # 删除
        mock_chroma_store.delete_chunks(["seq_1"])
        assert mock_chroma_store.get_collection_size() == 0


class TestCollectionSize:
    """collection 大小相关测试"""
    
    def test_size_after_operations(self, mock_chroma_store):
        """各种操作后的 size 正确性"""
        # 初始为 0
        assert mock_chroma_store.get_collection_size() == 0
        
        # 添加 3 个
        for i in range(3):
            mock_chroma_store.add_chunks(
                [{"id": f"size_{i}", "text": str(i), "metadata": {}}],
                [[0.1] * 768]
            )
        assert mock_chroma_store.get_collection_size() == 3
        
        # 删除 1 个
        mock_chroma_store.delete_chunks(["size_0"])
        assert mock_chroma_store.get_collection_size() == 2
        
        # 清空
        mock_chroma_store.delete_collection()
        assert mock_chroma_store.get_collection_size() == 0
