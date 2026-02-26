"""
错题管理API

功能说明：
- 获取错题列表和统计
- 错题重练（部分/全部）
- AI 智能诊断分析（流式响应）
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models import QuizBatch, BatchAnswer, UserAnswerHistory
from app.services import ReviewService

# AI 诊断相关导入
from app.llm import get_llm_client, LLMError
from app.llm.streaming import StreamUsageCollector
from prompts import prompt_loader

router = APIRouter(prefix="/mistakes", tags=["错题管理"])


class RetryRequest(BaseModel):
    """错题重练请求"""
    user_id: str
    course_id: Optional[str] = None
    batch_size: int = 10


class RetryAllRequest(BaseModel):
    """全部错题重练请求"""
    user_id: str
    course_id: Optional[str] = None  # 可选，用于筛选特定课程的错题


class AnalyzeMistakesRequest(BaseModel):
    """
    AI 错题分析请求
    
    支持三种分析模式：
    - diagnostic: 深度诊断，分析知识盲区和薄弱环节
    - variation: 举一反三，生成变式题进行强化练习
    - planning: 复习规划，制定个性化复习路径
    """
    user_id: str
    course_id: Optional[str] = None
    analysis_type: Optional[str] = "diagnostic"  # diagnostic, planning, variation


@router.post("/analyze")
async def analyze_mistakes(
    request: AnalyzeMistakesRequest, 
    db: Session = Depends(get_db)
):
    """
    AI 智能错题专家会诊（流式响应）
    
    业务逻辑说明：
    - 使用现有 LLM 封装层（get_llm_client + StreamUsageCollector）
    - 支持三种分析模式：diagnostic（深度诊断）、variation（举一反三）、planning（复习规划）
    - 流式响应，返回 text/plain 格式
    - 自动限制分析题目数量，避免 token 超限
    
    Args:
        request: 包含 user_id、course_id（可选）和 analysis_type
    
    Returns:
        StreamingResponse: 流式文本响应
    """
    
    async def generate_stream():
        """生成流式响应的内部生成器"""
        try:
            # 发送初始消息，防止前端超时
            yield "🤖 正在连接 AI 专家系统...\n"
            
            # 1. 获取用户错题数据
            # 关键业务逻辑：使用 run_in_threadpool 执行阻塞的数据库操作
            yield "🔍 正在检索您的错题记录...\n"
            
            # 限制题目数量，避免 token 超限
            # - variation 模式只取 5 题（生成变式题需要更多 token）
            # - 其他模式取 20 题
            limit = 5 if request.analysis_type == "variation" else 20
            
            # 使用 run_in_threadpool 执行阻塞的数据库查询
            wrong_data = await run_in_threadpool(
                ReviewService.get_wrong_questions, 
                db, 
                request.user_id, 
                request.course_id, 
                limit
            )
            
            questions = wrong_data.get("questions", [])
            wrong_times = wrong_data.get("wrong_times", {})
            
            if not questions:
                yield "\n🎉 恭喜！您当前没有错题记录，无需进行会诊。请继续保持！"
                return
            
            # 2. 构建错题数据文本
            yield "📝 正在整理分析材料...\n"
            
            user_performance_data = ""
            for i, q in enumerate(questions, 1):
                # 获取用户最近一次的错误答案
                from sqlalchemy import func
                latest_answer = db.query(UserAnswerHistory.answer).filter(
                    UserAnswerHistory.user_id == request.user_id,
                    UserAnswerHistory.question_id == q.id,
                    UserAnswerHistory.is_correct == False
                ).order_by(UserAnswerHistory.answered_at.desc()).first()
                
                user_ans = latest_answer[0] if latest_answer else "未知"
                
                # 构建单题信息（使用分隔符防止 prompt 注入）
                user_performance_data += f"""
【题目 {i}】
题干: {q.content}
选项: {q.options}
正确答案: {q.correct_answer}
用户错误答案: {user_ans}
解析: {q.explanation or '无'}
---
"""
            
            # 3. 选择提示词模板
            # 关键业务逻辑：根据分析类型选择不同的 prompt 模板
            template_name = "diagnostic_analyzer"  # 默认
            
            if request.analysis_type == "planning":
                template_name = "study_planner"
            elif request.analysis_type == "variation":
                template_name = "question_generator"
            else:
                template_name = "diagnostic_analyzer"
            
            template_vars = {
                "user_performance_data": user_performance_data
            }
            
            # 4. 加载提示词模板
            try:
                messages_payload = prompt_loader.get_messages(
                    template_name,
                    include_templates=["analysis_context"],
                    **template_vars
                )
            except Exception as e:
                # 降级处理：使用简化的 prompt
                print(f"[API] Warning: Failed to load template '{template_name}': {e}")
                system_instruction = {
                    "diagnostic": "你是一位严谨的AI诊断专家。请分析学生的错题，指出其思维误区和逻辑漏洞。",
                    "variation": "你是一位资深的出题专家。请基于学生做错的题目，生成 1-3 道变式题。",
                    "planning": "你是一位专业的学习规划师。请根据学生的错题记录，制定复习计划。"
                }.get(request.analysis_type, "你是一位AI学习助手。")
                
                messages_payload = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"以下是我的错题记录，请进行分析：\n{user_performance_data}"}
                ]
            
            # 5. 调用 LLM 进行流式分析
            # 关键业务逻辑：使用现有 LLM 封装层，确保配置、监控、错误处理一致
            llm = get_llm_client()
            
            yield "💡 AI 思考中...\n\n"
            
            # 使用 StreamUsageCollector 处理流式响应
            stream = llm.chat_stream(
                messages_payload, 
                temperature=0.5, 
                max_tokens=2000
            )
            collector = StreamUsageCollector(stream)
            
            # 逐块输出内容
            async for chunk in collector.iter():
                if chunk.content:
                    yield chunk.content
            
            # 流结束后，usage 信息已在 collector.usage 中
            # 可在此处添加 Langfuse 追踪或日志记录
            if collector.usage:
                print(f"[API] AI诊断完成 - Token用量: input={collector.usage.input}, output={collector.usage.output}")
        
        except LLMError as e:
            # LLM 调用错误
            yield f"\n\n❌ AI 服务调用失败: {e.message}"
        except Exception as e:
            # 其他错误
            import traceback
            traceback.print_exc()
            yield f"\n\n❌ 发生错误: {str(e)}"
    
    return StreamingResponse(generate_stream(), media_type="text/plain")


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
            "user_answer": latest_answers.get(q.id),  # 从历史记录获取最新用户答案
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
    """
    重练部分错题
    
    Args:
        request: 包含 user_id、course_id（可选）和 batch_size
    
    Returns:
        dict: 包含 batch_id 和题目列表
    """
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
