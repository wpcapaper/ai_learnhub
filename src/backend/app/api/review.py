"""
复习调度API路由
实现艾宾浩斯智能刷题
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.review_service import ReviewService
from app.models import Question, UserLearningRecord


router = APIRouter(prefix="/review", tags=["复习调度"])


# Schemas
class AnswerSubmissionRequest(BaseModel):
    """答案提交请求"""
    question_id: str
    answer: str
    is_correct: bool


class QuestionWithRecord(BaseModel):
    """题目和记录"""
    id: str
    content: str
    question_type: str
    options: dict | list | None
    correct_answer: str
    explanation: str | None

    class Config:
        from_attributes = True


class ReviewStatsResponse(BaseModel):
    """复习统计响应"""
    due_count: int
    mastered_count: int


# Endpoints
@router.get("/next", response_model=List[QuestionWithRecord])
async def get_next_review_questions(
    user_id: str,
    course_id: Optional[str] = None,
    batch_size: int = 10,
    allow_new_round: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取下一批复习题目

    按艾宾浩斯记忆曲线优先级返回题目
    """
    questions = ReviewService.get_next_question(db, user_id, course_id, batch_size, allow_new_round)
    return questions


@router.post("/submit", response_model=dict)
async def submit_answer(
    request: AnswerSubmissionRequest,
    user_id: str,
    db: Session = Depends(get_db)
):
    """提交答案并更新复习进度"""
    record = ReviewService.submit_answer(
        db,
        user_id=user_id,
        question_id=request.question_id,
        answer=request.answer,
        is_correct=request.is_correct
    )
    return {
        "record_id": record.id,
        "review_stage": record.review_stage,
        "next_review_time": record.next_review_time.isoformat() if record.next_review_time else None,
        "message": "答题记录已更新"
    }


@router.get("/stats", response_model=ReviewStatsResponse)
async def get_review_stats(user_id: str, db: Session = Depends(get_db)):
    """获取复习统计"""
    due_count = ReviewService.get_due_questions_count(db, user_id)
    mastered_questions = ReviewService.get_mastered_questions(db, user_id)
    return ReviewStatsResponse(
        due_count=due_count,
        mastered_count=len(mastered_questions)
    )


@router.get("/queue")
async def get_review_queue(
    user_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取复习队列

    按复习优先级排序的所有待复习题目
    """
    queue = ReviewService.get_review_queue(db, user_id, limit)
    return [
        {
            "question": {
                "id": q.id,
                "content": q.content,
                "question_type": q.question_type,
                "options": q.options,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation
            },
            "record": {
                "id": r.id,
                "is_correct": r.is_correct,
                "review_stage": r.review_stage,
                "next_review_time": r.next_review_time.isoformat() if r.next_review_time else None,
                "answered_at": r.answered_at.isoformat() if r.answered_at else None
            }
        }
        for q, r in queue
    ]


@router.get("/mastered")
async def get_mastered_questions(user_id: str, db: Session = Depends(get_db)):
    """获取已掌握的题目列表"""
    questions = ReviewService.get_mastered_questions(db, user_id)
    return [
        {
            "id": q.id,
            "content": q.content,
            "question_type": q.question_type,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation
        }
        for q in questions
    ]
