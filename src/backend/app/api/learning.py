"""
学习课程API
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from collections.abc import AsyncGenerator
from typing import Optional, cast, Any
from pydantic import BaseModel

from app.core.database import get_db, SessionLocal
from app.models import Chapter, Course
from app.rag import retrieve_chapter_chunks, retrieve_course_chunks, build_rag_context
from app.services import LearningService
from prompts import prompt_loader

# LLM 客户端（使用新的封装层）
from app.llm import get_llm_client
from app.llm.streaming import StreamUsageCollector


router = APIRouter(prefix="/learning", tags=["学习课程"])


# 请求模型
class ProgressUpdate(BaseModel):
    """进度更新请求"""
    position: int  # 阅读位置（字符偏移量）
    percentage: float  # 阅读百分比（0-100）


class ChatRequest(BaseModel):
    """AI对话请求"""
    chapter_id: str  # 章节 ID
    message: str  # 用户消息
    user_id: Optional[str] = None  # 用户 ID（可选）
    conversation_id: Optional[str] = None  # 会话 ID（可选，用于延续对话）




@router.get("/{course_id}/chapters")
def get_chapters(
    course_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定课程的所有章节列表

    Args:
        course_id: 课程 ID
        db: 数据库会话

    Returns:
        List[dict]: 章节列表

    Raises:
        404: 当课程不存在时
    """
    try:
        chapters = LearningService.get_chapters(db, course_id)
        result = [
            {
                "id": c.id,
                "course_id": c.course_id,
                "title": c.title,
                "sort_order": c.sort_order,
            }
            for c in chapters
        ]
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{chapter_id}/content")
def get_chapter_content(
    chapter_id: str,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取章节内容，如果提供了用户 ID，则同时返回用户的阅读进度

    Args:
        chapter_id: 章节 ID
        user_id: 用户 ID（可选）
        db: 数据库会话

    Returns:
        dict: 包含章节内容和用户进度的字典

    Raises:
        404: 当章节不存在时
    """
    try:
        content = LearningService.get_chapter_content(db, user_id, chapter_id)
        return content
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{chapter_id}/progress")
def update_progress(
    chapter_id: str,
    progress: ProgressUpdate,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    更新用户的阅读进度

    Args:
        chapter_id: 章节 ID
        progress: 进度更新数据
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        dict: 更新后的阅读进度

    Raises:
        404: 当章节不存在时
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="用户 ID 不能为空")

    try:
        updated_progress = LearningService.update_reading_progress(
            db,
            user_id,
            chapter_id,
            progress.position,
            progress.percentage
        )
        last_read_at_value = cast(Optional[datetime], getattr(updated_progress, "last_read_at", None))
        last_read_at_iso = last_read_at_value.isoformat() if isinstance(last_read_at_value, datetime) else None
        return {
            "id": updated_progress.id,
            "user_id": updated_progress.user_id,
            "chapter_id": updated_progress.chapter_id,
            "last_position": updated_progress.last_position,
            "last_percentage": updated_progress.last_percentage,
            "is_completed": updated_progress.is_completed,
            "last_read_at": last_read_at_iso,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{chapter_id}/complete")
def mark_chapter_completed(
    chapter_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    标记章节为已完成

    Args:
        chapter_id: 章节 ID
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        dict: 更新后的阅读进度

    Raises:
        404: 当章节不存在时
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="用户 ID 不能为空")

    try:
        updated_progress = LearningService.mark_chapter_completed(db, user_id, chapter_id)
        last_read_at_value = cast(Optional[datetime], getattr(updated_progress, "last_read_at", None))
        last_read_at_iso = last_read_at_value.isoformat() if isinstance(last_read_at_value, datetime) else None
        return {
            "id": updated_progress.id,
            "user_id": updated_progress.user_id,
            "chapter_id": updated_progress.chapter_id,
            "is_completed": updated_progress.is_completed,
            "last_read_at": last_read_at_iso,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{course_id}/progress")
def get_user_progress(
    course_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    获取用户在指定课程中的学习进度摘要

    Args:
        course_id: 课程 ID
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        dict: 包含课程进度信息的字典

    Raises:
        404: 当课程不存在时
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="用户 ID 不能为空")

    try:
        progress = LearningService.get_user_progress_summary(db, user_id, course_id)
        return progress
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ai/chat")
async def ai_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    AI 课程助手对话接口（流式响应）
    已接入 DeepSeek-V3 大模型，支持 Langfuse 监控
    """
    
    if not request.chapter_id:
        raise HTTPException(status_code=400, detail="章节 ID 不能为空")
    if not request.message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    chapter = db.query(Chapter).filter(
        Chapter.id == request.chapter_id,
        Chapter.is_deleted.is_(False)
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail=f"章节 {request.chapter_id} 不存在")

    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.is_deleted.is_(False)
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail=f"课程 {chapter.course_id} 不存在")

    conversation_id = request.conversation_id
    if not conversation_id:
        conversation = LearningService.create_conversation(db, request.user_id, request.chapter_id)
        conversation_id = conversation.id
    conversation_id_value: str = str(conversation_id)
    
    LearningService.save_message(db, conversation_id_value, "user", request.message)

    max_history = prompt_loader.get_config("ai_assistant_rag", "variables", {}).get("max_history", 10)
    history_messages = LearningService.get_conversation_history(db, conversation_id_value, limit=max_history)
    
    # 获取 LLM 客户端
    try:
        llm = get_llm_client()
    except ValueError as err:
        error_msg = str(err)
        async def missing_config_stream():
            yield f"⚠️ {error_msg}"
        return StreamingResponse(missing_config_stream(), media_type="text/plain")

    async def generate_stream():
        """
        生成流式响应
        使用独立的数据库会话，避免会话生命周期问题
        集成 Langfuse 监控
        """
        from app.llm.langfuse_wrapper import _get_langfuse_client
        from datetime import datetime as dt
        from app.models.user import User
        
        db_stream = SessionLocal()
        langfuse_client = _get_langfuse_client()
        trace = None
        start_time = dt.now()
        
        # 获取用户昵称用于 Langfuse 追踪
        # 注意：当前开发阶段使用 nickname 便于在 Langfuse 中直观识别用户
        # 后续生产化应改为使用 user_id，因为 nickname 可能重复或变更
        user_nickname: Optional[str] = None
        if request.user_id:
            user = db_stream.query(User).filter(User.id == request.user_id).first()
            if user:
                user_nickname = str(user.nickname) if user.nickname is not None else None
        trace_user_id: Optional[str] = user_nickname
        if trace_user_id is None and request.user_id is not None:
            trace_user_id = str(request.user_id)
        
        course_code_value = str(course.code)
        sort_order_value = cast(Optional[int], chapter.sort_order)
        chapter_order = sort_order_value if sort_order_value is not None and sort_order_value > 0 else None
        chapter_chunks = await retrieve_chapter_chunks(
            query=request.message,
            course_code=course_code_value,
            top_k=5,
            score_threshold=0.0,
            chapter_order=chapter_order
        )
        course_chunks = await retrieve_course_chunks(
            query=request.message,
            course_code=course_code_value,
            top_k=5,
            score_threshold=0.0
        )
        chapter_context = build_rag_context(chapter_chunks, max_context_chars=2000)
        course_context = build_rag_context(course_chunks, max_context_chars=2000)

        chapter_block = "【当前章节召回】\n" + (chapter_context or "未检索到相关内容。")
        course_block = "【课程维度召回】\n" + (course_context or "未检索到相关内容。")
        course_content = f"{chapter_block}\n\n{course_block}"

        messages_payload = prompt_loader.get_messages(
            "ai_assistant_rag",
            include_templates=["course_context"],
            course_content=course_content
        )

        for msg in history_messages:
            messages_payload.append({"role": msg["role"], "content": msg["content"]})

        # 提取 system prompt 和 user messages
        # 注意：messages_payload 可能包含多条 system 消息（如 system_prompt + course_context）
        system_parts = []
        user_messages = []
        for msg in messages_payload:
            if msg.get("role") == "system":
                system_parts.append(msg.get("content", ""))
            else:
                user_messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content", "")[:200],  # 截断避免过长
                })
        
        # 合并所有 system 消息为完整的 prompt
        full_system_prompt = "\n\n".join(system_parts) if system_parts else None
        
        # 准备 trace 输入数据（包含完整的 prompt 信息）
        input_data = {
            "user_message": request.message,
            "chapter_id": request.chapter_id,
            "system_prompt": full_system_prompt,  # 合并后的完整 system prompt
            "conversation_history_count": len(user_messages) - 1 if user_messages else 0,  # 历史消息数
        }
        
        # 创建 Langfuse trace（包含 user 信息）
        if langfuse_client:
            trace = langfuse_client.trace(
                name="ai_chat",
                input=input_data,
                user_id=trace_user_id,
                tags=["assistant", "course"],
            )
        
        full_response_content = ""
        error_occurred = None
        collector: Optional[StreamUsageCollector] = None
        
        try:
            stream = cast(AsyncGenerator[Any, None], llm.chat_stream(
                messages_payload,
                temperature=0.7,
                max_tokens=2000
            ))
            collector = StreamUsageCollector(stream)
            async for chunk in collector.iter():
                if chunk.content:
                    full_response_content += chunk.content
                    yield chunk.content
            
            # 保存助手回复到数据库
            LearningService.save_message(db_stream, conversation_id_value, "assistant", full_response_content)
            db_stream.commit()

        except Exception as e:
            error_occurred = str(e)
            yield f"\n\n❌ AI 服务调用失败: {str(e)}"
        finally:
            db_stream.close()
            
            # 记录 trace 到 Langfuse（在流结束后更新完整输出）
            if langfuse_client and trace:
                end_time = dt.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                output_data = {
                    "response_length": len(full_response_content),
                    "response_preview": full_response_content[:500] if full_response_content else None,
                }
                
                if error_occurred:
                    output_data["error"] = error_occurred
                
                # 使用 generation 类型记录 LLM 调用（支持 usage 统计）
                trace.generation(
                    name="llm_call",
                    input=input_data,
                    output=output_data,
                    model=llm.default_model,
                    usage=collector.usage if collector else None,
                    start_time=start_time,
                    end_time=end_time,
                    metadata={
                        "duration_ms": duration_ms,
                        "temperature": 0.7,
                        "max_tokens": 2000,
                    },
                )
                
                # 更新 trace 的 output
                trace.update(output=output_data)
                
                langfuse_client.flush()
    
    response = StreamingResponse(generate_stream(), media_type="text/plain")
    response.headers["X-Conversation-Id"] = conversation_id_value
    return response
