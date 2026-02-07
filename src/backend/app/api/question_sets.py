"""
题集管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import QuestionSet, Question
from app.services import QuestionSetService

router = APIRouter(prefix="/question-sets", tags=["题集管理"])


@router.get("", response_model=List[dict])
def get_question_sets(
    course_id: str,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取课程的题集列表

    Args:
        course_id: 课程ID
        active_only: 是否只返回启用的题集（默认True）
        db: 数据库会话

    Returns:
        List[dict]: 题集列表
    """
    question_sets = QuestionSetService.get_question_sets(db, course_id, active_only)

    return [
        {
            "id": qs.id,
            "course_id": qs.course_id,
            "code": qs.code,
            "name": qs.name,
            "description": qs.description,
            "total_questions": qs.total_questions,
            "is_active": qs.is_active,
            "created_at": qs.created_at.isoformat() if qs.created_at else None
        }
        for qs in question_sets
    ]


@router.get("/{set_code}/questions", response_model=List[dict])
def get_question_set_questions(
    set_code: str,
    db: Session = Depends(get_db)
):
    """
    获取固定题集的题目

    Args:
        set_code: 题集代码
        db: 数据库会话

    Returns:
        List[dict]: 题目列表
    """
    question_set = QuestionSetService.get_question_set_by_code(db, set_code)

    if not question_set:
        raise HTTPException(status_code=404, detail="题集不存在")

    question_ids = question_set.fixed_question_ids
    questions = db.query(Question).filter(
        Question.id.in_(question_ids),
        Question.is_deleted == False
    ).all()

    return [
        {
            "id": q.id,
            "content": q.content,
            "question_type": q.question_type,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "knowledge_points": q.knowledge_points,
            "difficulty": q.difficulty
        }
        for q in questions
    ]
