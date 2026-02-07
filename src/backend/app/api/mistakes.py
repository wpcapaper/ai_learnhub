"""
错题管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models import QuizBatch, BatchAnswer, UserAnswerHistory
from app.services import ReviewService

router = APIRouter(prefix="/mistakes", tags=["错题管理"])


class RetryRequest(BaseModel):
    user_id: str
    course_id: Optional[str] = None
    batch_size: int = 10


class RetryAllRequest(BaseModel):
    """全部错题重练请求"""
    user_id: str
    course_id: Optional[str] = None  # 可选，用于筛选特定课程的错题


@router.get("", response_model=List[dict])
def get_wrong_questions(
    user_id: str,
    course_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取错题列表

    Args:
        user_id: 用户ID
        course_id: 课程ID（可选）
        db: 数据库会话

    Returns:
        List[dict]: 错题列表，包含最近的做错时间
    """
    wrong_data = ReviewService.get_wrong_questions(db, user_id, course_id)
    wrong_questions = wrong_data["questions"]
    wrong_times = wrong_data["wrong_times"]

    question_ids = [q.id for q in wrong_questions]

    # 从历史记录表获取最新答案（UserAnswerHistory）
    latest_answers = {}
    if question_ids:
        # 子查询：找出每个题目最近一次答题记录
        from sqlalchemy import func
        latest_answer_subquery = (
            db.query(
                UserAnswerHistory.question_id.label('q_id'),
                func.max(UserAnswerHistory.answered_at).label('ans_at')
            )
            .filter(
                UserAnswerHistory.user_id == user_id,
                UserAnswerHistory.question_id.in_(question_ids)
            )
            .group_by(UserAnswerHistory.question_id)
            .subquery()
        )

        # 查询最新答案
        records = (
            db.query(
                UserAnswerHistory.question_id,
                UserAnswerHistory.answer
            )
            .join(
                latest_answer_subquery,
                UserAnswerHistory.question_id == latest_answer_subquery.c.q_id
            )
            .filter(
                UserAnswerHistory.answered_at == latest_answer_subquery.c.ans_at
            )
            .all()
        )
        latest_answers = {r.question_id: r.answer for r in records}

    # 获取题集信息（用于标注题目来源）
    from app.models import QuestionSet
    question_set_codes = {}
    # 获取所有课程的题集，然后为每道题找到对应的题集
    course_ids = list(set(q.course_id for q in wrong_questions))
    all_question_sets = db.query(QuestionSet).filter(QuestionSet.course_id.in_(course_ids)).all()
    for qs in all_question_sets:
        if qs.fixed_question_ids:
            for qid in qs.fixed_question_ids:
                if qid not in question_set_codes:
                    question_set_codes[qid] = []
                question_set_codes[qid].append(qs.name)  # 返回题集名称而非code

    return [
        {
            "id": q.id,
            "content": q.content,
            "question_type": q.question_type,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "difficulty": q.difficulty,
            "course_id": q.course_id,
            "course": {
                "id": q.course.id,
                "title": q.course.title
            } if q.course else None,
            "answer": latest_answers.get(q.id),  # 从历史记录获取最新答案
            "last_wrong_time": wrong_times.get(q.id),
            "question_set_codes": question_set_codes.get(q.id, [])  # 返回题集来源
        }
        for q in wrong_questions
    ]


@router.get("/stats", response_model=dict)
def get_mistakes_stats(
    user_id: str,
    course_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取错题统计

    Args:
        user_id: 用户ID
        course_id: 课程ID（可选）
        db: 数据库会话

    Returns:
        dict: 错题统计
            {
                "total_wrong": int,
                "wrong_by_course": {course_id: count},
                "wrong_by_type": {question_type: count}
            }
    """
    wrong_data = ReviewService.get_wrong_questions(db, user_id, course_id)
    wrong_questions = wrong_data["questions"]

    # 按课程统计
    wrong_by_course = {}
    for q in wrong_questions:
        course_id = q.course_id
        wrong_by_course[course_id] = wrong_by_course.get(course_id, 0) + 1

    # 按题型统计
    wrong_by_type = {}
    for q in wrong_questions:
        q_type = q.question_type
        wrong_by_type[q_type] = wrong_by_type.get(q_type, 0) + 1

    return {
        "total_wrong": len(wrong_questions),
        "wrong_by_course": wrong_by_course,
        "wrong_by_type": wrong_by_type
    }


@router.post("/retry", response_model=dict)
def retry_wrong_questions(
    request: RetryRequest,
    db: Session = Depends(get_db)
):
    wrong_data = ReviewService.get_wrong_questions(db, request.user_id, request.course_id)
    wrong_questions = wrong_data["questions"]

    if not wrong_questions:
        raise HTTPException(status_code=404, detail="没有错题可重做")

    questions_to_retry = wrong_questions[:request.batch_size]

    import uuid
    from datetime import datetime

    batch = QuizBatch(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        batch_size=len(questions_to_retry),
        mode="practice",
        started_at=datetime.utcnow(),
        status="in_progress"
    )
    db.add(batch)
    db.flush()

    for question in questions_to_retry:
        answer = BatchAnswer(
            id=str(uuid.uuid4()),
            batch_id=batch.id,
            question_id=question.id,
            user_answer=None,
            is_correct=None,
            answered_at=None
        )
        db.add(answer)

    db.commit()
    db.refresh(batch)

    return {
        "batch_id": batch.id,
        "questions": [
            {
                "id": q.id,
                "content": q.content,
                "question_type": q.question_type,
                "options": q.options
            }
            for q in questions_to_retry
        ]
    }


@router.post("/retry-all", response_model=dict)
def retry_all_wrong_questions(
    request: RetryAllRequest,
    db: Session = Depends(get_db)
):
    """
    重练错题本中的全部错题

    业务逻辑说明：
    - 获取错题本中的所有错题（无数量限制）
    - 创建刷题批次，批次大小 = 错题总数
    - 支持按课程筛选（course_id参数）
    - 复用现有的QuizBatch和BatchAnswer模型
    - 与现有错题重练接口/mistakes/retry完全解耦，不污染已有功能

    Args:
        request: 包含user_id和可选的course_id

    Returns:
        dict: 包含batch_id和题目列表
            {
                "batch_id": "批次ID",
                "questions": [...],  # 所有错题
                "total_count": 错题总数
            }
    """
    import uuid
    from datetime import datetime

    # 获取错题本中的所有错题（不限制数量）
    # 关键业务逻辑：使用limit=10000确保获取所有错题，而非默认的100条
    wrong_data = ReviewService.get_wrong_questions(
        db, request.user_id, request.course_id, limit=10000
    )
    wrong_questions = wrong_data["questions"]

    # 如果没有错题，返回提示
    if not wrong_questions:
        raise HTTPException(status_code=404, detail="没有错题可重练")

    # 创建批次，批次大小 = 错题总数
    # 关键业务逻辑：创建包含所有错题的批次，而不是默认的10题批次
    # 使用mode="mistakes_retry"标识这是错题重练批次，与普通练习模式区分
    batch = QuizBatch(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        batch_size=len(wrong_questions),
        mode="mistakes_retry",
        started_at=datetime.utcnow(),
        status="in_progress"
    )
    db.add(batch)
    db.flush()

    # 为每道错题创建答题记录
    # 关键业务逻辑：批次包含错题本中的所有错题，确保用户可以一次性重练所有错题
    for question in wrong_questions:
        answer = BatchAnswer(
            id=str(uuid.uuid4()),
            batch_id=batch.id,
            question_id=question.id,
            user_answer=None,
            is_correct=None,
            answered_at=None
        )
        db.add(answer)

    db.commit()
    db.refresh(batch)

    return {
        "batch_id": batch.id,
        "questions": [
            {
                "id": q.id,
                "content": q.content,
                "question_type": q.question_type,
                "options": q.options
            }
            for q in wrong_questions
        ],
        "total_count": len(wrong_questions)
    }
