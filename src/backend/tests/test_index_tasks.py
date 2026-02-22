"""
索引任务单元测试

测试覆盖：
1. index_chapter - 单章节索引
2. index_course - 批量课程索引
3. generate_wordcloud - 词云生成
4. generate_knowledge_graph - 知识图谱生成
5. generate_quiz - Quiz 生成
6. 分布式锁机制
7. 版本控制

注意：这些测试使用 Mock 隔离外部依赖（chromadb 等）
"""
import pytest
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock, patch, AsyncMock
import tempfile

from conftest import MockChromaVectorStore, MockEmbeddingModel, MockRAGService


# 模块级别的 mock，避免导入 chromadb
@pytest.fixture(autouse=True, scope="module")
def mock_rag_imports():
    """自动 mock RAG 相关导入"""
    with patch.dict('sys.modules', {
        'chromadb': MagicMock(),
        'chromadb.config': MagicMock(),
    }):
        yield


class TestIndexChapter:
    """index_chapter 任务测试"""
    
    def test_index_chapter_basic(self, tmp_path):
        """基本章节索引"""
        # Create course dir structure matching jobs.py expectations
        # jobs.py does: Path(__file__).parent.parent.parent / "courses"
        # So we need to create the structure accordingly
        courses_dir = tmp_path / "courses" / "test_course"
        courses_dir.mkdir(parents=True)
        
        chapter_file = courses_dir / "ch01.md"
        chapter_file.write_text("# 测试章节\n\n这是测试内容。" * 50)
        
        mock_store = MagicMock()
        mock_store.get_legacy_chunk_ids.return_value = []
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.RAGService') as MockRAGService:
                mock_service = MagicMock()
                mock_service.persist_directory = str(tmp_path / "chroma")
                mock_service.index_course_content = AsyncMock(return_value=5)
                MockRAGService.get_instance.return_value = mock_service
                
                with patch('app.tasks.jobs.ChromaVectorStore', return_value=mock_store):
                    with patch('app.tasks.jobs.SessionLocal') as MockSession:
                        mock_db = MagicMock()
                        mock_db.query.return_value.filter.return_value.first.return_value = None
                        MockSession.return_value = mock_db
                        
                        # Patch __file__ in the jobs module to point to our temp structure
                        with patch('app.tasks.jobs.__file__', str(tmp_path / "app" / "tasks" / "jobs.py")):
                            # Create fake jobs.py location structure
                            fake_app_dir = tmp_path / "app" / "tasks"
                            fake_app_dir.mkdir(parents=True)
                            
                            # Link/copy courses dir to expected location
                            import shutil
                            dest_courses = tmp_path / "app" / "courses"
                            if dest_courses.exists():
                                shutil.rmtree(dest_courses)
                            shutil.copytree(tmp_path / "courses", dest_courses)
                            
                            from app.tasks.jobs import index_chapter
                            
                            result = index_chapter(
                                chapter_id="ch01",
                                course_id="test_course",
                                chapter_file="ch01.md"
                            )
        
        assert result is not None
        assert "status" in result
    
    def test_index_chapter_file_not_found(self):
        """章节文件不存在时抛出异常"""
        mock_store = MagicMock()
        mock_store.get_legacy_chunk_ids.return_value = []
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.RAGService') as MockRAGService:
                mock_service = MagicMock()
                mock_service.persist_directory = "/tmp/chroma"
                mock_service.index_course_content = AsyncMock(return_value=5)
                MockRAGService.get_instance.return_value = mock_service
                
                with patch('app.tasks.jobs.ChromaVectorStore', return_value=mock_store):
                    with patch('app.tasks.jobs.SessionLocal') as MockSession:
                        mock_db = MagicMock()
                        mock_db.query.return_value.filter.return_value.first.return_value = None
                        MockSession.return_value = mock_db
                        
                        # Patch __file__ to point to a non-existent location
                        with patch('app.tasks.jobs.__file__', '/nonexistent/path/jobs.py'):
                            from app.tasks.jobs import index_chapter
                            
                            with pytest.raises(ValueError, match="章节文件不存在"):
                                index_chapter(
                                    chapter_id="ch01",
                                    course_id="test_course",
                                    chapter_file="nonexistent.md"
                                )
    
    def test_index_chapter_clears_legacy_chunks(self):
        """索引后删除旧版本 chunks"""
        mock_store = MagicMock()
        mock_store.get_legacy_chunk_ids.return_value = ["old_1", "old_2"]
        mock_store.delete_chunks = MagicMock()
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.RAGService') as MockRAGService:
                mock_service = MagicMock()
                mock_service.persist_directory = "/tmp/chroma"
                mock_service.index_course_content = AsyncMock(return_value=3)
                MockRAGService.get_instance.return_value = mock_service
                
                with patch('app.tasks.jobs.ChromaVectorStore', return_value=mock_store):
                    with patch('app.tasks.jobs.SessionLocal') as MockSession:
                        mock_db = MagicMock()
                        mock_db.query.return_value.filter.return_value.first.return_value = None
                        MockSession.return_value = mock_db
                        
                        with patch('pathlib.Path') as MockPath:
                            mock_path_instance = MagicMock()
                            mock_path_instance.exists.return_value = True
                            mock_path_instance.read_text.return_value = "内容"
                            mock_path_instance.__truediv__ = lambda self, x: mock_path_instance
                            MockPath.return_value = mock_path_instance
                            MockPath.__truediv__ = lambda self, x: mock_path_instance
                            
                            with patch('asyncio.run', return_value=3):
                                from app.tasks.jobs import index_chapter
                                
                                result = index_chapter(
                                    chapter_id="ch01",
                                    course_id="test_course",
                                    chapter_file="ch01.md"
                                )
        
        mock_store.delete_chunks.assert_called_once_with(["old_1", "old_2"])


class TestIndexCourse:
    """index_course 批量索引测试"""
    
    def test_index_course_multiple_chapters(self):
        """批量索引多个章节"""
        chapters = [
            {"chapter_id": "ch1", "temp_ref": "course/ch01.md", "chapter_file": "ch01.md"},
            {"chapter_id": "ch2", "temp_ref": "course/ch02.md", "chapter_file": "ch02.md"},
        ]
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.acquire_course_lock', return_value=True):
                with patch('app.tasks.jobs.release_course_lock'):
                    with patch('app.tasks.jobs.index_chapter') as mock_index:
                        mock_index.return_value = {"chunk_count": 5, "status": "success"}
                        
                        from app.tasks.jobs import index_course
                        
                        result = index_course(
                            course_id="test_course",
                            chapters=chapters
                        )
        
        assert result["total_chapters"] == 2
        assert mock_index.call_count == 2
    
    def test_index_course_locked_skips(self):
        """课程被锁定时跳过"""
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.acquire_course_lock', return_value=False):
                from app.tasks.jobs import index_course
                
                result = index_course(
                    course_id="locked_course",
                    chapters=[{"chapter_id": "ch1", "chapter_file": "ch01.md"}]
                )
        
        assert result["error"] == "课程正在被其他任务处理"
        assert result["success_count"] == 0
    
    def test_index_course_partial_failure(self):
        """部分章节失败时继续处理"""
        chapters = [
            {"chapter_id": "ch1", "chapter_file": "ch01.md"},
            {"chapter_id": "ch2", "chapter_file": "ch02.md"},
            {"chapter_id": "ch3", "chapter_file": "ch03.md"},
        ]
        
        call_count = [0]
        
        def mock_index_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("索引失败")
            return {"chunk_count": 5, "status": "success"}
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.acquire_course_lock', return_value=True):
                with patch('app.tasks.jobs.release_course_lock'):
                    with patch('app.tasks.jobs.index_chapter', side_effect=mock_index_side_effect):
                        from app.tasks.jobs import index_course
                        
                        result = index_course(
                            course_id="test_course",
                            chapters=chapters
                        )
        
        assert result["success_count"] == 2
        assert result["failed_count"] == 1
    
    def test_index_course_first_chapter_clears(self):
        """只有第一章清除已有数据"""
        chapters = [
            {"chapter_id": "ch1", "chapter_file": "ch01.md"},
            {"chapter_id": "ch2", "chapter_file": "ch02.md"},
        ]
        
        captured_configs = []
        
        def capture_config(*args, **kwargs):
            captured_configs.append(kwargs.get('config', {}))
            return {"chunk_count": 5, "status": "success"}
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.acquire_course_lock', return_value=True):
                with patch('app.tasks.jobs.release_course_lock'):
                    with patch('app.tasks.jobs.index_chapter', side_effect=capture_config):
                        from app.tasks.jobs import index_course
                        
                        index_course(
                            course_id="test_course",
                            chapters=chapters,
                            config={"clear_existing": True}
                        )
        
        assert captured_configs[0].get("clear_existing") is True
        assert captured_configs[1].get("clear_existing") is False


class TestGenerateWordcloud:
    """词云生成测试"""
    
    def test_generate_wordcloud_basic(self):
        """基本词云生成"""
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            from app.tasks.jobs import generate_wordcloud
            
            result = generate_wordcloud(
                chapter_id="ch01",
                course_id="test_course"
            )
        
        assert "image_url" in result
        assert "created_at" in result
    
    def test_generate_wordcloud_with_config(self):
        """带配置的词云生成"""
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            from app.tasks.jobs import generate_wordcloud
            
            config = {
                "width": 1024,
                "height": 768,
                "max_words": 200
            }
            
            result = generate_wordcloud(
                chapter_id="ch01",
                course_id="test_course",
                config=config
            )
        
        assert result["config"]["width"] == 1024


class TestGenerateKnowledgeGraph:
    """知识图谱生成测试"""
    
    def test_generate_knowledge_graph_basic(self):
        """基本知识图谱生成"""
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            from app.tasks.jobs import generate_knowledge_graph
            
            result = generate_knowledge_graph(
                chapter_id="ch01",
                course_id="test_course"
            )
        
        assert "graph_url" in result
        assert "nodes" in result
        assert "edges" in result


class TestGenerateQuiz:
    """Quiz 生成测试"""
    
    def test_generate_quiz_basic(self):
        """基本 Quiz 生成"""
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            from app.tasks.jobs import generate_quiz
            
            result = generate_quiz(
                chapter_id="ch01",
                course_id="test_course"
            )
        
        assert "questions" in result
        assert "count" in result


class TestTraceHelpers:
    """Trace 辅助函数测试"""
    
    def test_create_trace_no_client(self):
        """无 Langfuse 客户端时返回 None"""
        # Patch at the source where _get_langfuse_client is defined
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            from app.tasks.jobs import _create_trace
            
            result = _create_trace("test", ["tag"])
        
        assert result == (None, None, None)
    
    def test_finish_trace_no_client(self):
        """无 Langfuse 客户端时不报错"""
        from app.tasks.jobs import _finish_trace
        
        _finish_trace(None, None, None, {}, {})
    
    def test_finish_trace_with_error(self):
        """带错误的 trace 记录"""
        from app.tasks.jobs import _finish_trace
        
        mock_client = MagicMock()
        mock_trace = MagicMock()
        start_time = datetime.now()
        
        _finish_trace(
            mock_client,
            mock_trace,
            start_time,
            {"input": "data"},
            {"output": "data"},
            error="测试错误"
        )
        
        # Verify trace.span was called
        mock_trace.span.assert_called_once()


class TestDatabaseUpdate:
    """数据库状态更新测试"""
    
    def test_update_kb_config_on_success(self):
        """索引成功时更新 KB 配置"""
        mock_kb_config = MagicMock()
        mock_kb_config.index_status = "pending"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_kb_config
        
        mock_store = MagicMock()
        mock_store.get_legacy_chunk_ids.return_value = []
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.RAGService') as MockRAGService:
                mock_service = MagicMock()
                mock_service.persist_directory = "/tmp/chroma"
                MockRAGService.get_instance.return_value = mock_service
                
                with patch('app.tasks.jobs.ChromaVectorStore', return_value=mock_store):
                    with patch('app.tasks.jobs.SessionLocal', return_value=mock_db):
                        with patch('pathlib.Path') as MockPath:
                            mock_path_instance = MagicMock()
                            mock_path_instance.exists.return_value = True
                            mock_path_instance.read_text.return_value = "内容"
                            mock_path_instance.__truediv__ = lambda self, x: mock_path_instance
                            MockPath.return_value = mock_path_instance
                            MockPath.__truediv__ = lambda self, x: mock_path_instance
                            
                            with patch('asyncio.run', return_value=5):
                                from app.tasks.jobs import index_chapter
                                
                                index_chapter(
                                    chapter_id="temp_ref_value",
                                    course_id="test_course",
                                    chapter_file="ch01.md"
                                )
        
        assert mock_kb_config.index_status == "indexed"
        assert mock_kb_config.chunk_count == 5
        mock_db.commit.assert_called_once()
    
    def test_update_kb_config_on_failure(self):
        """索引失败时更新错误状态"""
        mock_kb_config = MagicMock()
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_kb_config
        
        with patch('app.llm.langfuse_wrapper._get_langfuse_client', return_value=None):
            with patch('app.tasks.jobs.RAGService') as MockRAGService:
                MockRAGService.get_instance.side_effect = Exception("服务初始化失败")
                
                with patch('app.tasks.jobs.SessionLocal', return_value=mock_db):
                    from app.tasks.jobs import index_chapter
                    
                    with pytest.raises(Exception):
                        index_chapter(
                            chapter_id="ch01",
                            course_id="test_course",
                            chapter_file="ch01.md"
                        )
        
        assert mock_kb_config.index_status == "failed"
        assert "服务初始化失败" in mock_kb_config.index_error
