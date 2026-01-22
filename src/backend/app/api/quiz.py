"""
批次刷题API路由
实现批次刷题和统一对答案
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.quiz_service import QuizService
from app.models import QuizBatch


router = APIRouter(prefix="/quiz", tags=["批次刷题"])


# Schemas
class StartBatchRequest(BaseModel):
    """开始批次请求"""
    mode: str = "practice"
    batch_size: int = 10
    course_id: str = None


class BatchAnswerRequest(BaseModel):
    """批次答题请求"""
    question_id: str
    answer: str


class QuestionInBatchResponse(BaseModel):
    """批次中的题目响应"""
    id: str
    content: str
    question_type: str
    options: dict | None
    correct_answer: str | None
    explanation: str | None
    user_answer: str | None
    is_correct: bool | None
    answered_at: str | None


class BatchResultResponse(BaseModel):
    """批次结果响应"""
    batch_id: str
    total: int
    correct: int
    wrong: int
    accuracy: float


class BatchInfoResponse(BaseModel):
    """批次信息响应"""
    id: str
    user_id: str
    batch_size: int
    mode: str
    started_at: str
    completed_at: str | None
    status: str


# Endpoints
@router.post("/start", response_model=BatchInfoResponse, status_code=status.HTTP_201_CREATED)
async def start_batch(
    request: StartBatchRequest,
    user_id: str,
    db: Session = Depends(get_db)
):
    """开始一个新的刷题批次"""
    try:
        batch = QuizService.start_batch(
            db,
            user_id=user_id,
            mode=request.mode,
            batch_size=request.batch_size,
            course_id=request.course_id
        )
        return BatchInfoResponse(
            id=batch.id,
            user_id=batch.user_id,
            batch_size=batch.batch_size,
            mode=batch.mode,
            started_at=batch.started_at.isoformat() if batch.started_at else None,
            completed_at=batch.completed_at.isoformat() if batch.completed_at else None,
            status=batch.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/answer", response_model=dict)
async def submit_batch_answer(
    request: BatchAnswerRequest,
    user_id: str,
    batch_id: str,
    db: Session = Depends(get_db)
):
    """提交批次中的单题答案"""
    try:
        answer = QuizService.submit_batch_answer(
            db,
            user_id=user_id,
            batch_id=batch_id,
            question_id=request.question_id,
            answer=request.answer
        )
        return {
            "answer_id": answer.id,
            "question_id": answer.question_id,
            "user_answer": answer.user_answer,
            "answered_at": answer.answered_at.isoformat() if answer.answered_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/finish", response_model=BatchResultResponse)
async def finish_batch(
    user_id: str,
    batch_id: str,
    db: Session = Depends(get_db)
):
    """完成批次（统一对答案）"""
    try:
        result = QuizService.finish_batch(db, user_id, batch_id)
        return BatchResultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{batch_id}/questions", response_model=List[QuestionInBatchResponse])
async def get_batch_questions(
    user_id: str,
    batch_id: str,
    db: Session = Depends(get_db)
):
    """获取批次中的题目和答题状态"""
    try:
        questions = QuizService.get_batch_questions(db, user_id, batch_id)
        return [QuestionInBatchResponse(**q) for q in questions]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/batches", response_model=List[BatchInfoResponse])
async def list_batches(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """列出用户的所有批次"""
    batches = QuizService.list_batches(db, user_id, limit)
    return [
        BatchInfoResponse(
            id=b.id,
            user_id=b.user_id,
            batch_size=b.batch_size,
            mode=b.mode,
            started_at=b.started_at.isoformat() if b.started_at else None,
            completed_at=b.completed_at.isoformat() if b.completed_at else None,
            status=b.status
        )
        for b in batches
    ]


@router.get("/{batch_id}", response_model=BatchInfoResponse)
async def get_batch_info(
    user_id: str,
    batch_id: str,
    db: Session = Depends(get_db)
):
    """获取批次信息"""
    batch = db.query(QuizBatch).filter(
        QuizBatch.id == batch_id,
        QuizBatch.user_id == user_id
    ).first()

    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    return BatchInfoResponse(
        id=batch.id,
        user_id=batch.user_id,
        batch_size=batch.batch_size,
        mode=batch.mode,
        started_at=batch.started_at.isoformat() if batch.started_at else None,
        completed_at=batch.completed_at.isoformat() if batch.completed_at else None,
        status=batch.status
    )
