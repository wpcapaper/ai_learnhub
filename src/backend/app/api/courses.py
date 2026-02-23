"""
课程管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models import Course, Question, UserLearningRecord, UserCourseProgress, Chapter
from app.services import CourseService
from sqlalchemy import func

router = APIRouter(prefix="/courses", tags=["课程管理"])


@router.get("", response_model=List[dict])
def get_courses(
    active_only: bool = True,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取课程列表

    Args:
        active_only: 是否只返回启用的课程（默认True）
        user_id: 用户ID（可选，用于返回已刷题目统计）
        db: 数据库会话

    Returns:
        List[dict]: 课程列表
    """
    courses = CourseService.get_courses(db, active_only)

    result = []
    
    for c in courses:
        # 临时过滤：如果 course_type 是 'exam'，则跳过
        if c.course_type == 'exam':
            continue

        course_data = {
            "id": c.id,
            "code": c.code,
            "title": c.title,
            "description": c.description,
            "course_type": c.course_type,
            "cover_image": c.cover_image,
            "default_exam_config": c.default_exam_config,
            "is_active": c.is_active,
            "sort_order": c.sort_order,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }

        if user_id:
            # 移除 course_type == 'exam' 限制，让所有课程都能显示题目统计
            total_questions = db.query(func.count(Question.id)).filter(
                Question.course_id == c.id,
                Question.is_deleted == False
            ).scalar() or 0
            
            subquery = db.query(Question.id).filter(
                Question.course_id == c.id,
                Question.is_deleted == False
            )

            # 修复：只统计当前轮次已刷过的题目数量（completed_in_current_round = True）
            # 而不是所有历史已答题目数量
            answered_questions = db.query(func.count(UserLearningRecord.question_id.distinct())).filter(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.question_id.in_(subquery),
                UserLearningRecord.completed_in_current_round == True  # 当前轮次已刷过
            ).scalar() or 0

            course_data["total_questions"] = total_questions
            course_data["answered_questions"] = answered_questions

            # 新增：获取轮次信息
            progress = db.query(UserCourseProgress).filter(
                UserCourseProgress.user_id == user_id,
                UserCourseProgress.course_id == c.id
            ).first()

            # 关键业务逻辑：即使没有进度记录，也返回默认值
            # 确保前端显示"第 1 轮"而不是其他异常
            if progress:
                course_data["current_round"] = progress.current_round
                course_data["total_rounds_completed"] = progress.total_rounds_completed
            else:
                course_data["current_round"] = 1
                course_data["total_rounds_completed"] = 0

        result.append(course_data)

    return result


@router.get("/{course_id}", response_model=dict)
def get_course(
    course_id: str,
    db: Session = Depends(get_db)
):
    """
    获取课程详情

    Args:
        course_id: 课程ID
        db: 数据库会话

    Returns:
        dict: 课程详情
    """
    course = CourseService.get_course_by_id(db, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    return {
        "id": course.id,
        "code": course.code,
        "title": course.title,
        "description": course.description,
        "course_type": course.course_type,
        "cover_image": course.cover_image,
        "default_exam_config": course.default_exam_config,
        "is_active": course.is_active,
        "sort_order": course.sort_order,
        "created_at": course.created_at.isoformat() if course.created_at else None
    }


# ==================== 词云 API (用户端) ====================
# 用户端只提供词云数据读取功能，生成功能在管理端
# API 设计：
#   - /{id}/...        → 通过 UUID 查询（C端使用，后端自动查库转换 code）
#   - /by-code/{code}/... → 通过 code 查询（管理端使用，直接访问目录）

import os
import json
from pathlib import Path


def get_markdown_courses_dir() -> Path:
    """获取 markdown_courses 目录路径（词云文件存储位置）"""
    docker_path = Path("/app/markdown_courses")
    if docker_path.exists():
        return docker_path
    # 本地开发环境：相对于 backend/app/api 目录
    return Path(__file__).parent.parent.parent.parent / "markdown_courses"


# ==================== 内部工具函数 ====================

def _resolve_course_code(course_id_or_code: str, db: Session) -> tuple:
    """
    解析课程标识符，返回 (code, course_dir)
    
    支持两种输入：
    - course.code (如 'llm_basic') → 直接使用
    - course.id (UUID) → 查数据库获取 code
    
    Args:
        course_id_or_code: 课程 UUID 或 code
        db: 数据库会话
    
    Returns:
        tuple[str, Path]: (课程代码, 课程目录路径)
        
    Raises:
        ValueError: 课程不存在
    """
    markdown_dir = get_markdown_courses_dir()
    
    # 1. 尝试作为目录名（code）
    course_dir = markdown_dir / course_id_or_code
    if course_dir.exists() and course_dir.is_dir():
        return (course_id_or_code, course_dir)
    
    # 2. 尝试作为 UUID 查数据库
    course = db.query(Course).filter(Course.id == course_id_or_code).first()
    if course:
        code = course.code
        course_dir = markdown_dir / code
        if course_dir.exists():
            return (code, course_dir)
    
    raise ValueError(f"课程不存在: {course_id_or_code}")


def _get_chapter_file_name(course_code: str, sort_order: int) -> str:
    """
    从 course.json 获取指定 sort_order 的章节文件名
    
    Args:
        course_code: 课程代码（目录名）
        sort_order: 章节排序号
    
    Returns:
        章节文件名（不含扩展名），未找到返回 None
    """
    markdown_dir = get_markdown_courses_dir()
    course_json_path = markdown_dir / course_code / "course.json"
    
    if not course_json_path.exists():
        return None
    
    try:
        with open(course_json_path, 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        
        for ch in course_json.get("chapters", []):
            if ch.get("sort_order") == sort_order:
                # 返回文件名（不含扩展名）
                from pathlib import Path as PathLib
                return PathLib(ch.get("file", "")).stem
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


def _get_course_wordcloud_by_code(course_code: str) -> dict:
    """内部函数：通过 code 获取课程词云数据"""
    from app.services.wordcloud_service import WordcloudService
    
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_code
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程目录不存在")
    
    wc_service = WordcloudService(courses_dir=str(markdown_dir))
    wordcloud = wc_service.get_course_wordcloud(course_dir)
    
    if not wordcloud:
        raise HTTPException(status_code=404, detail="词云未生成")
    
    return wordcloud


def _get_course_wordcloud_status_by_code(course_code: str) -> dict:
    """内部函数：通过 code 获取课程词云状态"""
    from app.services.wordcloud_service import WordcloudService
    
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_code
    
    if not course_dir.exists():
        return {"has_wordcloud": False, "generated_at": None, "words_count": 0}
    
    wc_service = WordcloudService(courses_dir=str(markdown_dir))
    has_wordcloud = wc_service.has_course_wordcloud(course_dir)
    
    if has_wordcloud:
        data = wc_service.get_course_wordcloud(course_dir)
        return {
            "has_wordcloud": True,
            "generated_at": data.get("generated_at"),
            "words_count": len(data.get("words", []))
        }
    return {"has_wordcloud": False, "generated_at": None, "words_count": 0}


def _get_chapter_wordcloud_by_code(course_code: str, file_name: str) -> dict:
    """内部函数：通过 code + file_name 获取章节词云数据"""
    from app.services.wordcloud_service import WordcloudService
    
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_code
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程目录不存在")
    
    wc_service = WordcloudService(courses_dir=str(markdown_dir))
    wordcloud = wc_service.get_chapter_wordcloud(course_dir, file_name)
    
    if not wordcloud:
        raise HTTPException(status_code=404, detail="章节词云未生成")
    
    return wordcloud


def _get_chapter_wordcloud_status_by_code(course_code: str, file_name: str) -> dict:
    """内部函数：通过 code + file_name 获取章节词云状态"""
    from app.services.wordcloud_service import WordcloudService
    
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_code
    
    if not course_dir.exists():
        return {"has_wordcloud": False, "generated_at": None, "words_count": 0}
    
    wc_service = WordcloudService(courses_dir=str(markdown_dir))
    
    if wc_service.has_chapter_wordcloud(course_dir, file_name):
        data = wc_service.get_chapter_wordcloud(course_dir, file_name)
        return {
            "has_wordcloud": True,
            "generated_at": data.get("generated_at"),
            "words_count": len(data.get("words", []))
        }
    return {"has_wordcloud": False, "generated_at": None, "words_count": 0}


# ==================== 课程词云 API ====================

# --- C端 API：通过 UUID 查询 ---

@router.get("/{course_id}/wordcloud/status")
def get_course_wordcloud_status_by_id(course_id: str, db: Session = Depends(get_db)):
    """
    通过课程 UUID 获取词云状态（C端使用）
    
    Args:
        course_id: 课程 UUID
    Returns:
        词云状态信息
    """
    try:
        code, _ = _resolve_course_code(course_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return _get_course_wordcloud_status_by_code(code)


@router.get("/{course_id}/wordcloud")
def get_course_wordcloud_by_id(course_id: str, db: Session = Depends(get_db)):
    """
    通过课程 UUID 获取词云数据（C端使用）
    
    Args:
        course_id: 课程 UUID
    Returns:
        词云完整数据
    """
    try:
        code, _ = _resolve_course_code(course_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return _get_course_wordcloud_by_code(code)


# --- 管理端 API：通过 code 查询 ---

@router.get("/by-code/{course_code}/wordcloud/status")
def get_course_wordcloud_status_by_code_api(course_code: str):
    """
    通过课程 code 获取词云状态（管理端使用）
    
    Args:
        course_code: 课程代码（目录名）
    Returns:
        词云状态信息
    """
    return _get_course_wordcloud_status_by_code(course_code)


@router.get("/by-code/{course_code}/wordcloud")
def get_course_wordcloud_by_code_api(course_code: str):
    """
    通过课程 code 获取词云数据（管理端使用）
    
    Args:
        course_code: 课程代码（目录名）
    Returns:
        词云完整数据
    """
    return _get_course_wordcloud_by_code(course_code)


# ==================== 章节词云 API ====================

# --- C端 API：通过 UUID 查询 ---

@router.get("/{course_id}/chapters/{chapter_id}/wordcloud/status")
def get_chapter_wordcloud_status_by_ids(
    course_id: str,
    chapter_id: str,
    db: Session = Depends(get_db)
):
    """
    通过 UUID 获取章节词云状态（C端使用）
    
    Args:
        course_id: 课程 UUID
        chapter_id: 章节 UUID
    Returns:
        词云状态信息
    """
    try:
        course_code, _ = _resolve_course_code(course_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # 查询章节获取 sort_order
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        return {"has_wordcloud": False, "generated_at": None, "words_count": 0}
    
    # 从 course.json 获取文件名
    file_name = _get_chapter_file_name(course_code, chapter.sort_order)
    if not file_name:
        return {"has_wordcloud": False, "generated_at": None, "words_count": 0}
    
    return _get_chapter_wordcloud_status_by_code(course_code, file_name)


@router.get("/{course_id}/chapters/{chapter_id}/wordcloud")
def get_chapter_wordcloud_by_ids(
    course_id: str,
    chapter_id: str,
    db: Session = Depends(get_db)
):
    """
    通过 UUID 获取章节词云数据（C端使用）
    
    Args:
        course_id: 课程 UUID
        chapter_id: 章节 UUID
    Returns:
        词云完整数据
    """
    try:
        course_code, _ = _resolve_course_code(course_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # 查询章节获取 sort_order
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    
    # 从 course.json 获取文件名
    file_name = _get_chapter_file_name(course_code, chapter.sort_order)
    if not file_name:
        raise HTTPException(status_code=404, detail="章节文件不存在")
    
    return _get_chapter_wordcloud_by_code(course_code, file_name)


# --- 管理端 API：通过 code + file_name 查询 ---

@router.get("/by-code/{course_code}/chapters/{file_name}/wordcloud/status")
def get_chapter_wordcloud_status_by_code_api(course_code: str, file_name: str):
    """
    通过 code + file_name 获取章节词云状态（管理端使用）
    
    Args:
        course_code: 课程代码
        file_name: 章节文件名（不含扩展名）
    Returns:
        词云状态信息
    """
    return _get_chapter_wordcloud_status_by_code(course_code, file_name)


@router.get("/by-code/{course_code}/chapters/{file_name}/wordcloud")
def get_chapter_wordcloud_by_code_api(course_code: str, file_name: str):
    """
    通过 code + file_name 获取章节词云数据（管理端使用）
    
    Args:
        course_code: 课程代码
        file_name: 章节文件名（不含扩展名）
    Returns:
        词云完整数据
    """
    return _get_chapter_wordcloud_by_code(course_code, file_name)
