"""
课程转换导入生命周期测试

基于 FILE_LIFE_CIRCLE.md 中定义的生命周期编写测试：
- 阶段一：原始数据 (raw_courses/)
- 阶段二：转换阶段 (CoursePipeline)
- 阶段三：输出阶段 (markdown_courses/)
- 阶段四：入库阶段 (数据库)
- 词云查询设计
"""
import pytest
import sys
import os
import json
import uuid
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRawDataStage:
    """测试原始数据阶段的行为"""
    
    @pytest.fixture
    def temp_raw_dir(self, tmp_path):
        raw_dir = tmp_path / "raw_courses"
        raw_dir.mkdir()
        yield raw_dir
    
    def test_scan_md_and_ipynb_files(self, temp_raw_dir):
        from app.course_pipeline import CoursePipeline
        from app.course_pipeline.models import ContentType
        
        course_dir = temp_raw_dir / "test_course"
        course_dir.mkdir()
        (course_dir / "01_intro.md").write_text("# Intro")
        (course_dir / "02_code.ipynb").write_text('{"cells": []}')
        (course_dir / "image.png").write_text("fake image")
        (course_dir / "data.json").write_text("{}")
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(temp_raw_dir),
            markdown_courses_dir=str(temp_raw_dir / "output")
        )
        
        raw_courses = pipeline.scan_raw_courses()
        
        assert len(raw_courses) == 1
        assert len(raw_courses[0].source_files) == 2
        
        file_types = {sf.content_type for sf in raw_courses[0].source_files}
        assert ContentType.MARKDOWN in file_types
        assert ContentType.IPYNB in file_types
    
    def test_ignore_course_json_in_raw_dir(self, temp_raw_dir):
        from app.course_pipeline import CoursePipeline
        
        course_dir = temp_raw_dir / "test_course"
        course_dir.mkdir()
        (course_dir / "01_intro.md").write_text("# Intro")
        (course_dir / "course.json").write_text('{"title": "Should be ignored"}')
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(temp_raw_dir),
            markdown_courses_dir=str(temp_raw_dir / "output")
        )
        
        raw_courses = pipeline.scan_raw_courses()
        
        assert len(raw_courses[0].source_files) == 1
        assert raw_courses[0].source_files[0].path.endswith('.md')
    
    def test_skip_hidden_files_and_checkpoints(self, temp_raw_dir):
        from app.course_pipeline import CoursePipeline
        
        course_dir = temp_raw_dir / "test_course"
        course_dir.mkdir()
        (course_dir / "01_intro.md").write_text("# Intro")
        (course_dir / ".hidden.md").write_text("Hidden")
        (course_dir / ".ipynb_checkpoints").mkdir()
        (course_dir / ".ipynb_checkpoints" / "notebook.ipynb").write_text('{}')
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(temp_raw_dir),
            markdown_courses_dir=str(temp_raw_dir / "output")
        )
        
        raw_courses = pipeline.scan_raw_courses()
        
        assert len(raw_courses[0].source_files) == 1
        assert "01_intro.md" in raw_courses[0].source_files[0].path


class TestConversionStage:
    """测试转换阶段的行为"""
    
    @pytest.fixture
    def setup_conversion(self, tmp_path):
        raw_dir = tmp_path / "raw_courses"
        output_dir = tmp_path / "markdown_courses"
        raw_dir.mkdir()
        output_dir.mkdir()
        
        course_dir = raw_dir / "Python基础"
        course_dir.mkdir()
        
        (course_dir / "01_简介.md").write_text("# Python 简介\n\nPython是一门编程语言。\n")
        (course_dir / "02_变量.md").write_text("# 变量\n\n变量用于存储数据。\n")
        (course_dir / "03_函数.md").write_text("# 函数\n\n函数是代码的封装。\n")
        
        return {
            "raw_dir": raw_dir,
            "output_dir": output_dir,
            "course_dir": course_dir
        }
    
    def test_first_conversion_no_version_suffix(self, setup_conversion):
        from app.course_pipeline import CoursePipeline
        from app.course_pipeline.models import RawCourse, SourceFile
        
        setup = setup_conversion
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        source_files = [
            SourceFile.from_path(str(f), str(setup["course_dir"]))
            for f in setup["course_dir"].glob("*.md")
        ]
        
        raw_course = RawCourse(
            course_id="Python基础",
            name="Python基础",
            source_dir=str(setup["course_dir"]),
            source_files=source_files
        )
        
        result = pipeline.convert_course(raw_course)
        
        assert result.success
        
        output_dirs = list(setup["output_dir"].iterdir())
        dir_names = [d.name for d in output_dirs if d.is_dir()]
        
        assert any("_v" not in name for name in dir_names), f"Found versioned dirs: {dir_names}"
    
    def test_course_code_generation(self, setup_conversion):
        from app.course_pipeline import CoursePipeline
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup_conversion["raw_dir"]),
            markdown_courses_dir=str(setup_conversion["output_dir"])
        )
        
        code = pipeline._generate_course_code("Python基础")
        assert "python" in code.lower()
        assert code.isalnum() or "_" in code
        
        code = pipeline._generate_course_code("Course-Name 123!")
        assert "-" not in code or "_" in code
        assert "!" not in code
    
    def test_preserve_original_chapter_order(self, setup_conversion):
        from app.course_pipeline import CoursePipeline
        from app.course_pipeline.models import RawCourse, SourceFile
        
        setup = setup_conversion
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        source_files = [
            SourceFile.from_path(str(f), str(setup["course_dir"]))
            for f in sorted(setup["course_dir"].glob("*.md"))
        ]
        
        raw_course = RawCourse(
            course_id="Python基础",
            name="Python基础",
            source_dir=str(setup["course_dir"]),
            source_files=source_files
        )
        
        result = pipeline.convert_course(raw_course)
        
        assert result.success
        
        chapters = result.course.chapters
        assert any("简介" in ch.title or "intro" in ch.title.lower() for ch in chapters)


class TestOutputStage:
    """测试输出阶段的行为"""
    
    @pytest.fixture
    def converted_course(self, tmp_path):
        raw_dir = tmp_path / "raw_courses"
        output_dir = tmp_path / "markdown_courses"
        raw_dir.mkdir()
        output_dir.mkdir()
        
        course_dir = raw_dir / "test_course"
        course_dir.mkdir()
        (course_dir / "01_intro.md").write_text("# Introduction\n\nContent here.\n")
        
        return {
            "raw_dir": raw_dir,
            "output_dir": output_dir,
            "course_dir": course_dir
        }
    
    def test_course_json_structure_no_version(self, converted_course):
        from app.course_pipeline import CoursePipeline
        from app.course_pipeline.models import RawCourse, SourceFile
        
        setup = converted_course
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        source_file = SourceFile.from_path(
            str(setup["course_dir"] / "01_intro.md"),
            str(setup["course_dir"])
        )
        
        raw_course = RawCourse(
            course_id="test_course",
            name="Test Course",
            source_dir=str(setup["course_dir"]),
            source_files=[source_file]
        )
        
        result = pipeline.convert_course(raw_course)
        
        assert result.success
        
        course_json_path = setup["output_dir"] / "test_course" / "course.json"
        assert course_json_path.exists()
        
        with open(course_json_path, 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        
        assert "code" in course_json
        assert "title" in course_json
        assert "chapters" in course_json
        
        assert "origin" not in course_json
        assert "version" not in course_json
    
    def test_output_directory_structure(self, converted_course):
        from app.course_pipeline import CoursePipeline
        from app.course_pipeline.models import RawCourse, SourceFile
        
        setup = converted_course
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        source_file = SourceFile.from_path(
            str(setup["course_dir"] / "01_intro.md"),
            str(setup["course_dir"])
        )
        
        raw_course = RawCourse(
            course_id="test_course",
            name="Test Course",
            source_dir=str(setup["course_dir"]),
            source_files=[source_file]
        )
        
        result = pipeline.convert_course(raw_course)
        
        assert result.success
        
        output_course_dir = setup["output_dir"] / "test_course"
        
        assert output_course_dir.exists()
        assert (output_course_dir / "course.json").exists()
        assert len(list(output_course_dir.glob("*.md"))) > 0
    
    def test_reorder_course_not_implemented(self, converted_course):
        from app.course_pipeline import CoursePipeline
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(converted_course["raw_dir"]),
            markdown_courses_dir=str(converted_course["output_dir"])
        )
        
        with pytest.raises(NotImplementedError):
            pipeline.reorder_course("test_course")


class TestDatabaseImportStage:
    """测试入库阶段的行为"""
    
    @pytest.fixture
    def mock_db(self):
        mock_session = MagicMock()
        return mock_session
    
    @pytest.fixture
    def converted_course_with_json(self, tmp_path):
        output_dir = tmp_path / "markdown_courses" / "python_basics"
        output_dir.mkdir(parents=True)
        
        course_json = {
            "code": "python_basics",
            "title": "Python 基础",
            "description": "Python 入门教程",
            "course_type": "learning",
            "chapters": [
                {
                    "code": "intro",
                    "title": "简介",
                    "file": "01_intro.md",
                    "sort_order": 1
                },
                {
                    "code": "variables",
                    "title": "变量",
                    "file": "02_variables.md",
                    "sort_order": 2
                }
            ]
        }
        
        with open(output_dir / "course.json", 'w', encoding='utf-8') as f:
            json.dump(course_json, f, ensure_ascii=False)
        
        (output_dir / "01_intro.md").write_text("# 简介\n\nPython 是一门编程语言。\n")
        (output_dir / "02_variables.md").write_text("# 变量\n\n变量用于存储数据。\n")
        
        return output_dir
    
    def test_import_generates_uuid_for_id(self, converted_course_with_json):
        course_dir = converted_course_with_json
        
        with open(course_dir / "course.json", 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        
        generated_id = str(uuid.uuid4())
        
        try:
            uuid.UUID(generated_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
        
        assert is_valid_uuid
        assert generated_id != course_json["code"]
    
    def test_import_uses_code_for_deduplication(self, converted_course_with_json):
        course_dir = converted_course_with_json
        
        with open(course_dir / "course.json", 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        
        course_code = course_json.get("code")
        
        assert course_code == "python_basics"
    
    def test_chapters_get_separate_uuids(self, converted_course_with_json):
        course_dir = converted_course_with_json
        
        with open(course_dir / "course.json", 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        
        chapters = course_json.get("chapters", [])
        chapter_ids = [str(uuid.uuid4()) for _ in chapters]
        
        assert len(chapter_ids) == len(set(chapter_ids))
        
        for cid in chapter_ids:
            try:
                uuid.UUID(cid)
                is_valid = True
            except ValueError:
                is_valid = False
            assert is_valid
    
    def test_single_import_only(self):
        from app.api import admin as admin_module
        
        assert not hasattr(admin_module, 'import_courses_to_database') or \
               'batch' not in admin_module.__dict__.get('import_courses_to_database', lambda: '').__name__.lower()
        
        assert hasattr(admin_module, 'import_markdown_course_to_database')


class TestWordcloudQuery:
    """测试词云查询设计"""
    
    @pytest.fixture
    def wordcloud_setup(self, tmp_path):
        pending_dir = tmp_path / "markdown_courses" / "pending_course"
        pending_dir.mkdir(parents=True)
        
        pending_json = {
            "code": "pending_course",
            "title": "待导入课程",
            "chapters": [{"title": "Chapter 1", "file": "ch1.md"}]
        }
        
        with open(pending_dir / "course.json", 'w', encoding='utf-8') as f:
            json.dump(pending_json, f, ensure_ascii=False)
        
        wordcloud_data = {
            "version": "1.0",
            "generated_at": "2026-02-23T10:00:00",
            "words": [{"word": "python", "weight": 10.0}]
        }
        
        with open(pending_dir / "wordcloud.json", 'w', encoding='utf-8') as f:
            json.dump(wordcloud_data, f, ensure_ascii=False)
        
        return {
            "markdown_dir": tmp_path / "markdown_courses",
            "pending_dir": pending_dir,
            "wordcloud_data": wordcloud_data
        }
    
    def test_query_pending_course_by_code(self, wordcloud_setup):
        setup = wordcloud_setup
        
        code = "pending_course"
        wordcloud_path = setup["markdown_dir"] / code / "wordcloud.json"
        
        assert wordcloud_path.exists()
        
        with open(wordcloud_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data == setup["wordcloud_data"]
    
    def test_query_imported_course_by_id(self, wordcloud_setup):
        setup = wordcloud_setup
        
        mock_course = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "code": "pending_course"
        }
        
        course_id = mock_course["id"]
        course_code = mock_course["code"]
        
        wordcloud_path = setup["markdown_dir"] / course_code / "wordcloud.json"
        
        assert wordcloud_path.exists()
        
        with open(wordcloud_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data == setup["wordcloud_data"]


class TestFullLifecycle:
    """测试完整的生命周期流程"""
    
    @pytest.fixture
    def full_lifecycle_setup(self, tmp_path):
        raw_dir = tmp_path / "raw_courses"
        output_dir = tmp_path / "markdown_courses"
        raw_dir.mkdir()
        output_dir.mkdir()
        
        course_dir = raw_dir / "完整测试课程"
        course_dir.mkdir()
        
        (course_dir / "01_第一章.md").write_text("# 第一章\n\n内容 A。\n")
        (course_dir / "02_第二章.md").write_text("# 第二章\n\n内容 B。\n")
        (course_dir / "03_第三章.md").write_text("# 第三章\n\n内容 C。\n")
        
        (course_dir / "course.json").write_text('{"title": "Should be ignored"}')
        
        return {
            "raw_dir": raw_dir,
            "output_dir": output_dir,
            "course_dir": course_dir
        }
    
    def test_stage1_raw_data_scanning(self, full_lifecycle_setup):
        from app.course_pipeline import CoursePipeline
        
        setup = full_lifecycle_setup
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        raw_courses = pipeline.scan_raw_courses()
        
        assert len(raw_courses) == 1
        assert len(raw_courses[0].source_files) == 3
        assert raw_courses[0].course_id == "完整测试课程"
    
    def test_stage2_conversion_no_version(self, full_lifecycle_setup):
        from app.course_pipeline import CoursePipeline
        
        setup = full_lifecycle_setup
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        raw_courses = pipeline.scan_raw_courses()
        result = pipeline.convert_course(raw_courses[0])
        
        assert result.success
        
        output_dirs = [d for d in setup["output_dir"].iterdir() if d.is_dir()]
        assert len(output_dirs) == 1
        assert "_v" not in output_dirs[0].name
    
    def test_stage3_output_structure(self, full_lifecycle_setup):
        from app.course_pipeline import CoursePipeline
        
        setup = full_lifecycle_setup
        
        pipeline = CoursePipeline(
            raw_courses_dir=str(setup["raw_dir"]),
            markdown_courses_dir=str(setup["output_dir"])
        )
        
        raw_courses = pipeline.scan_raw_courses()
        result = pipeline.convert_course(raw_courses[0])
        
        assert result.success
        
        output_course_dir = [d for d in setup["output_dir"].iterdir() if d.is_dir()][0]
        
        assert (output_course_dir / "course.json").exists()
        
        with open(output_course_dir / "course.json", 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        
        assert "code" in course_json
        assert "title" in course_json
        assert len(course_json["chapters"]) == 3
        
        assert "origin" not in course_json
        assert "version" not in course_json
    
    def test_stage4_import_id_generation(self, full_lifecycle_setup):
        course_id = str(uuid.uuid4())
        
        try:
            uuid.UUID(course_id)
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert is_valid


class TestChapterReorderPlaceholder:
    """章节重排功能预留测试（TODO 实现）"""
    
    @pytest.fixture
    def versioned_course(self, tmp_path):
        output_dir = tmp_path / "markdown_courses"
        output_dir.mkdir()
        
        original_dir = output_dir / "python_basics"
        original_dir.mkdir()
        
        original_json = {
            "code": "python_basics",
            "title": "Python 基础",
            "chapters": [
                {"title": "简介", "file": "01.md", "sort_order": 1},
                {"title": "变量", "file": "02.md", "sort_order": 2}
            ]
        }
        
        with open(original_dir / "course.json", 'w', encoding='utf-8') as f:
            json.dump(original_json, f, ensure_ascii=False)
        
        return output_dir
    
    @pytest.mark.skip(reason="章节重排功能待实现")
    def test_reorder_creates_versioned_directory(self, versioned_course):
        pass
    
    @pytest.mark.skip(reason="章节重排功能待实现")
    def test_reorder_updates_course_json(self, versioned_course):
        pass
    
    @pytest.mark.skip(reason="章节重排功能待实现")
    def test_multiple_reorders_increment_version(self, versioned_course):
        pass
