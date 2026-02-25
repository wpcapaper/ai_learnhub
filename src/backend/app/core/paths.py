"""
路径配置常量

统一管理项目中的目录路径，避免硬编码。
"""
import os
from pathlib import Path


def _get_project_root() -> Path:
    """获取项目根目录"""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path(__file__).resolve().parents[3]


# ==================== 目录常量 ====================

# 原始课程目录（未转换的 Markdown）
RAW_COURSES_DIR_NAME = "raw_courses"
RAW_COURSES_DIR = Path(os.environ.get(
    "RAW_COURSES_DIR",
    str(_get_project_root() / RAW_COURSES_DIR_NAME)
))

# 转换后的课程目录（用于知识库索引）
MARKDOWN_COURSES_DIR_NAME = "markdown_courses"
MARKDOWN_COURSES_DIR = Path(os.environ.get(
    "MARKDOWN_COURSES_DIR",
    str(_get_project_root() / MARKDOWN_COURSES_DIR_NAME)
))

# 课程数据目录（已废弃，保留兼容）
# 注意：新代码应使用 MARKDOWN_COURSES_DIR
COURSES_DIR_NAME = "courses"
COURSES_DIR = MARKDOWN_COURSES_DIR  # 指向 markdown_courses


# ==================== 课程 JSON 配置文件 ====================

COURSE_JSON_FILENAME = "course.json"


def get_markdown_courses_dir() -> Path:
    candidates = [
        MARKDOWN_COURSES_DIR,
        _get_project_root() / MARKDOWN_COURSES_DIR_NAME,
        Path.cwd() / MARKDOWN_COURSES_DIR_NAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return MARKDOWN_COURSES_DIR


def get_course_json_path(course_code: str) -> Path:
    """获取课程的 course.json 路径"""
    return get_markdown_courses_dir() / course_code / COURSE_JSON_FILENAME


def get_chapter_path(course_code: str, source_file: str) -> Path:
    """获取章节文件路径"""
    return get_markdown_courses_dir() / course_code / source_file
