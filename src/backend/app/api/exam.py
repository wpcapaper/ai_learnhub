"""
考试模式API路由
实现固定题集和规则抽取考试
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.exam_service import ExamService


router = APIRouter(prefix="/exam", tags=["考试模式"])


# Schemas
class StartExamRequest(BaseModel):
    """开始考试请求"""
    total_questions: int = 50
    difficulty_range: List[int] | None = None
    question_set_id: str | None = None
    course_id: str = None


class ExamQuestionResponse(BaseModel):
    """考试题目响应"""
    id: str
    content: str
    question_type: str
    options: dict | None
    correct_answer: str | None
    explanation: str | None
    user_answer: str | None
    is_correct: bool | None
    answered_at: str | None


class ExamResultResponse(BaseModel):
    """考试结果响应"""
    batch_id: str
    total: int
    correct: int
    wrong: int
    score: float


# Endpoints
@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_exam(
    request: StartExamRequest,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    开始一次考试

    业务逻辑说明：
    - 根据是否传递 question_set_id 自动决定考试模式
    - question_set_id 存在：使用固定题集模式（所有用户考相同题目）
    - question_set_id 不存在：使用动态抽取模式（按难度随机抽取）
    - 考试开始后，所有答案提交不立即判断对错，只有完成考试时才统一计算
    - user_id 通过查询参数传递，用于身份验证和数据隔离

    Args:
        request: 请求体，包含考试配置参数
        user_id: 用户ID（查询参数，必需）
        db: 数据库会话

    Returns:
        考试信息，包含 exam_id, 总题数, 模式, 开始时间, 状态
    """
    try:
        # 根据是否传递题集代码决定考试模式
        # 如果有 question_set_id，则使用固定题集模式；否则使用动态抽取模式
        exam_mode = "fixed_set" if request.question_set_id else "extraction"

        # 调用服务层创建考试
        batch = ExamService.start_exam(
            db,
            user_id=user_id,
            course_id=request.course_id,
            exam_mode=exam_mode,
            question_type_config=None,
            difficulty_range=request.difficulty_range,
            question_set_code=request.question_set_id
        )
        return {
            "exam_id": batch.id,
            "total_questions": batch.batch_size,
            "mode": batch.mode,
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "status": batch.status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{exam_id}/answer", response_model=dict)
async def submit_exam_answer(
    request: dict,
    user_id: str,
    exam_id: str,
    db: Session = Depends(get_db)
):
    """
    提交考试中的单题答案（考试进行中，不判断对错）

    业务逻辑说明：
    - 考试进行中只保存用户答案，不立即判断对错
    - 只有在完成考试时才统一计算成绩（finish_exam 接口）
    - 这样可以防止考试过程中看到正确答案，保证考试公平性
    - user_id 通过查询参数传递，用于身份验证和数据隔离

    Args:
        request: 请求体，包含 question_id 和 answer
        user_id: 用户ID（查询参数，必需）
        exam_id: 考试ID
        db: 数据库会话

    Returns:
        提交的答案信息
    """
    try:
        # 调用服务层提交答案，只记录不判断对错
        answer = ExamService.submit_exam_answer(
            db,
            user_id=user_id,
            batch_id=exam_id,
            question_id=request["question_id"],
            answer=request["answer"]
        )
        return {
            "answer_id": answer.id,
            "question_id": answer.question_id,
            "user_answer": answer.user_answer,
            "answered_at": answer.answered_at.isoformat() if answer.answered_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{exam_id}/finish", response_model=ExamResultResponse)
async def finish_exam(
    user_id: str,
    exam_id: str,
    db: Session = Depends(get_db)
):
    """
    完成考试（统一计算成绩）

    业务逻辑说明：
    - 考试过程中只保存答案，不计算成绩
    - 只有在完成考试时才统一判断对错并计算总分
    - 计算完成后更新所有题目的 is_correct 字段
    - 同时更新用户的学习记录（调用艾宾浩斯算法）
    - user_id 通过查询参数传递，用于身份验证和数据隔离

    Args:
        user_id: 用户ID（查询参数，必需）
        exam_id: 考试ID
        db: 数据库会话

    Returns:
        考试结果，包含 batch_id, 总题数, 正确数, 错误数, 得分
    """
    try:
        # 调用服务层完成考试，统一计算成绩
        result = ExamService.finish_exam(db, user_id, exam_id)
        return ExamResultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{exam_id}/questions", response_model=List[ExamQuestionResponse])
async def get_exam_questions(
    user_id: str,
    exam_id: str,
    show_answers: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取考试中的题目

    业务逻辑说明：
    - show_answers 参数控制是否显示正确答案和解析
    - 考试进行中（show_answers=false）：隐藏 correct_answer 和 explanation 字段
    - 考试完成后（show_answers=true）：显示完整的 correct_answer 和 explanation
    - 这样可以防止考试过程中看到答案，保证考试公平性
    - user_id 通过查询参数传递，用于身份验证和数据隔离

    Args:
        user_id: 用户ID（查询参数，必需）
        exam_id: 考试ID
        show_answers: 是否显示答案（默认false）
        db: 数据库会话

    Returns:
        题目列表
    """
    try:
        # 调用服务层获取题目，根据 show_answers 控制是否返回答案
        questions = ExamService.get_exam_questions(
            db, user_id, exam_id, show_answers
        )
        return [ExamQuestionResponse(**q) for q in questions]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
