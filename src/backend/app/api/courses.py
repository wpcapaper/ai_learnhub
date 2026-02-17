"""
课程管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models import Course, Question, UserLearningRecord, UserCourseProgress
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
