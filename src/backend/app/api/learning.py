"""
学习课程API
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db, SessionLocal
from app.models import Chapter
from app.services import LearningService
from prompts import prompt_loader

# LLM 客户端（使用新的封装层）
from app.llm import get_llm_client, trace_llm_call


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
        return {
            "id": updated_progress.id,
            "user_id": updated_progress.user_id,
            "chapter_id": updated_progress.chapter_id,
            "last_position": updated_progress.last_position,
            "last_percentage": updated_progress.last_percentage,
            "is_completed": updated_progress.is_completed,
            "last_read_at": updated_progress.last_read_at.isoformat() if updated_progress.last_read_at else None,
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
        return {
            "id": updated_progress.id,
            "user_id": updated_progress.user_id,
            "chapter_id": updated_progress.chapter_id,
            "is_completed": updated_progress.is_completed,
            "last_read_at": updated_progress.last_read_at.isoformat() if updated_progress.last_read_at else None,
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
        Chapter.is_deleted == False
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail=f"章节 {request.chapter_id} 不存在")

    markdown_content = chapter.content_markdown or ""

    conversation_id = request.conversation_id
    if not conversation_id:
        conversation = LearningService.create_conversation(db, request.user_id, request.chapter_id)
        conversation_id = conversation.id
    
    LearningService.save_message(db, conversation_id, "user", request.message)

    max_history = prompt_loader.get_config("ai_assistant", "variables", {}).get("max_history", 10)
    history_messages = LearningService.get_conversation_history(db, conversation_id, limit=max_history)
    
    messages_payload = prompt_loader.get_messages(
        "ai_assistant",
        include_templates=["course_context"],
        course_content=markdown_content
    )
    
    for msg in history_messages:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})

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
        
        db_stream = SessionLocal()
        langfuse_client = _get_langfuse_client()
        trace = None
        start_time = dt.now()
        
        # 准备 trace 输入数据
        input_data = {
            "user_message": request.message,
            "chapter_id": request.chapter_id,
            "messages_count": len(messages_payload),
        }
        
        # 创建 Langfuse trace
        if langfuse_client:
            trace = langfuse_client.trace(
                name="ai_chat",
                input=input_data,
                tags=["assistant", "course"],
            )
        
        full_response_content = ""
        error_occurred = None
        
        try:
            # 流式调用 LLM
            async for chunk in llm.chat_stream(
                messages_payload,
                temperature=0.7,
                max_tokens=2000
            ):
                if chunk.content:
                    full_response_content += chunk.content
                    yield chunk.content
            
            # 保存助手回复到数据库
            LearningService.save_message(db_stream, conversation_id, "assistant", full_response_content)
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
                
                # 添加 span 记录 LLM 调用详情
                trace.span(
                    name="llm_call",
                    input=input_data,
                    output=output_data,
                    start_time=start_time,
                    end_time=end_time,
                    metadata={
                        "duration_ms": duration_ms,
                        "model": "streaming",
                    },
                )
                
                # 更新 trace 的 output
                trace.update(output=output_data)
                
                langfuse_client.flush()
    
    response = StreamingResponse(generate_stream(), media_type="text/plain")
    response.headers["X-Conversation-Id"] = conversation_id
    return response
