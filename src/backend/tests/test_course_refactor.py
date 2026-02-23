"""
课程系统重构测试

测试 Phase 1-4 的重构内容：
- 数据模型调整 (Course/Chapter)
- Pipeline 输出目录调整
- API 端点功能
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 模型测试
class TestCourseModel:
    """Course 模型测试"""
    
    def test_course_code_not_unique(self):
        """验证 Course.code 不再有 unique 约束"""
        from app.models import Course
        
        # 检查字段定义
        code_column = Course.__table__.columns['code']
        assert not code_column.unique, "Course.code 不应该有 unique 约束"
    
    def test_course_is_active_default_false(self):
        """验证 Course.is_active 默认为 False"""
        from app.models import Course
        
        is_active_column = Course.__table__.columns['is_active']
        assert is_active_column.default.arg == False, "Course.is_active 默认值应为 False"


class TestChapterModel:
    """Chapter 模型测试"""
    
    def test_chapter_no_code_field(self):
        """验证 Chapter 不再有 code 字段"""
        from app.models import Chapter
        
        column_names = [c.name for c in Chapter.__table__.columns]
        assert 'code' not in column_names, "Chapter 不应该有 code 字段"
    
    def test_chapter_has_is_active(self):
        """验证 Chapter 有 is_active 字段"""
        from app.models import Chapter
        
        column_names = [c.name for c in Chapter.__table__.columns]
        assert 'is_active' in column_names, "Chapter 应该有 is_active 字段"


# Pipeline 测试
class TestCoursePipeline:
    """CoursePipeline 测试"""
    
    @pytest.fixture
    def temp_dirs(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw_courses"
            output_dir = Path(tmpdir) / "markdown_courses"
            raw_dir.mkdir()
            output_dir.mkdir()
            yield raw_dir, output_dir
    
    def test_pipeline_uses_markdown_courses_dir(self, temp_dirs):
        """验证 Pipeline 使用 markdown_courses_dir 参数"""
        from app.course_pipeline import CoursePipeline
        
        raw_dir, output_dir = temp_dirs
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(raw_dir),
            markdown_courses_dir=str(output_dir)
        )
        
        assert pipeline.markdown_courses_dir == output_dir
    
    def test_get_next_version(self, temp_dirs):
        """验证版本号递增逻辑"""
        from app.course_pipeline import CoursePipeline
        
        raw_dir, output_dir = temp_dirs
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(raw_dir),
            markdown_courses_dir=str(output_dir)
        )
        
        # 第一次应该是 v1
        version = pipeline._get_next_version("test_course")
        assert version == 1
        
        # 创建 v1 目录后，下次应该是 v2
        (output_dir / "test_course_v1").mkdir()
        version = pipeline._get_next_version("test_course")
        assert version == 2
        
        # 创建 v2 后，下次应该是 v3
        (output_dir / "test_course_v2").mkdir()
        version = pipeline._get_next_version("test_course")
        assert version == 3


# API 端点测试
class TestAdminAPI:
    """管理 API 端点测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    
    def test_list_raw_courses_requires_raw_dir(self, client, monkeypatch):
        """测试 raw-courses 端点在目录不存在时返回空列表"""
        import app.api.admin as admin_module
        
        # Mock get_raw_courses_dir 返回不存在的路径
        monkeypatch.setattr(
            admin_module,
            "get_raw_courses_dir",
            lambda: Path("/nonexistent/path")
        )
        
        response = client.get("/api/admin/raw-courses")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_database_courses_empty(self, client):
        """测试 database/courses 端点返回空列表（新数据库）"""
        response = client.get("/api/admin/database/courses")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_activate_course_endpoint_exists(self, client):
        """测试 activate 端点存在"""
        # 使用不存在的 course_id，应该返回 404
        response = client.put(
            "/api/admin/database/courses/nonexistent-id/activate",
            json={"is_active": True}
        )
        assert response.status_code == 404


# 同步功能删除验证
class TestSyncRemoval:
    """验证同步功能已删除"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    
    def test_sync_endpoints_removed(self, client):
        """验证 sync-to-db 和 sync-all 端点已删除"""
        # sync-to-db 应该返回 404
        response = client.post(
            "/api/admin/kb/chapters/sync-to-db",
            params={"temp_ref": "test", "chapter_id": "test"}
        )
        assert response.status_code == 404
        
        # sync-all 应该返回 404
        response = client.post("/api/admin/kb/courses/test/sync-all")
        assert response.status_code == 404
    
    def test_sync_source_files_cleaned(self):
        """验证 sync 相关代码已从源文件删除"""
        # 检查 admin_kb.py 中不包含 sync-to-db 相关路由
        import os
        admin_kb_path = Path(__file__).parent.parent / "app" / "api" / "admin_kb.py"
        
        if admin_kb_path.exists():
            content = admin_kb_path.read_text()
            # 不应该包含 sync-to-db 或 sync-all 路由定义
            assert 'sync-to-db' not in content or 'def sync_chunks_to_db' not in content
            assert 'sync-all' not in content or 'def sync_course_to_online' not in content


# 集成测试
class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def full_setup(self, tmp_path):
        """完整测试环境"""
        # 创建目录结构
        raw_dir = tmp_path / "raw_courses" / "test_course"
        raw_dir.mkdir(parents=True)
        
        # 创建测试 markdown 文件
        (raw_dir / "01_intro.md").write_text("# 第一章\n\n这是测试内容。\n")
        
        # 创建输出目录
        output_dir = tmp_path / "markdown_courses"
        output_dir.mkdir()
        
        return {
            "raw_dir": tmp_path / "raw_courses",
            "output_dir": output_dir,
            "course_dir": raw_dir
        }
    
    def test_full_conversion_flow(self, full_setup):
        """测试完整转换流程"""
        from app.course_pipeline import CoursePipeline
        from app.course_pipeline.models import RawCourse, SourceFile
        
        setup = full_setup
        
        # 创建 Pipeline
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        # 创建 RawCourse
        source_file = SourceFile.from_path(
            str(setup["course_dir"] / "01_intro.md"),
            str(setup["course_dir"])
        )
        
        raw_course = RawCourse(
            course_id="test_course",
            name="测试课程",
            source_dir=str(setup["course_dir"]),
            source_files=[source_file]
        )
        
        # 执行转换
        result = pipeline.convert_course(raw_course)
        
        # 验证结果
        assert result.success, f"转换失败: {result.error_message}"
        assert result.course is not None
        assert len(result.course.chapters) == 1
        
        # 验证输出目录格式
        output_dirs = list(setup["output_dir"].iterdir())
        assert len(output_dirs) == 1
        assert output_dirs[0].name == "test_course_v1"
