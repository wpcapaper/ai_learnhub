"""
学习课程API
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from openai import AsyncOpenAI

from app.core.database import get_db, SessionLocal
from app.models import Chapter
from app.services import LearningService


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
    已接入 DeepSeek-V3 大模型
    """
    
    # 参数验证
    if not request.chapter_id:
        raise HTTPException(status_code=400, detail="章节 ID 不能为空")
    if not request.message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    # 从数据库查询章节信息
    chapter = db.query(Chapter).filter(
        Chapter.id == request.chapter_id,
        Chapter.is_deleted == False
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail=f"章节 {request.chapter_id} 不存在")

    # 获取章节内容
    markdown_content = chapter.content_markdown or ""

    # 1. 管理会话 (Conversation)
    conversation_id = request.conversation_id
    if not conversation_id:
        # 如果没传 conversation_id，创建一个新的
        conversation = LearningService.create_conversation(db, request.user_id, request.chapter_id)
        conversation_id = conversation.id
    
    # 2. 保存用户消息
    LearningService.save_message(db, conversation_id, "user", request.message)

    # 3. 获取历史记录 (Context)
    # 获取最近 10 条历史消息（不包含刚才存的那条用户消息，因为我们会在 Prompt 里显式加上）
    history_messages = LearningService.get_conversation_history(db, conversation_id, limit=10)
    # 过滤掉刚才那条最新的，避免重复（因为 get_conversation_history 会包含刚刚存的）
    # 简单的做法是：get_conversation_history 逻辑里是按时间倒序取 limit，再反转。
    # 只要 limit 足够大，或者我们在 Prompt 构建时小心处理。
    # 更严谨的做法：在 Prompt 里，history 是一部分，current_user_message 是最后一部分。
    
    # 构建 OpenA 格式的消息列表
    messages_payload = [
        {"role": "system", "content": (
            "你是一个专业的 AI 助教，负责解答用户关于课程内容的问题。\n"
            "你的回答应该准确、简洁，并优先基于提供的【课程内容片段】进行解答。\n\n"
            "【语气与行为准则】\n"
            "1. 专业且富有耐心：像一位循羡诱导的导师，专注于帮助用户理解知识点。\n"
            "2. 聚焦课程：如果用户发起闲聊，请礼貌地回应并将话题自然地引回课程内容。\n"
            "3. 上下文连贯：参考历史对话记录，确保回答逻辑一致。\n"
            "4. 知识优先：通过精准的知识解答体现智能。\n\n"
            "【重要：后续问题推荐】\n"
            "在回答结束后，请根据当前上下文，生成3个用户可能会继续追问的短问题。\n"
            "格式要求：在回答的最末尾，必须严格按照以下格式输出（包括分隔符）：\n"
            "<<SUGGESTED_QUESTIONS>>\n"
            "[\"问题1\", \"问题2\", \"问题3\"]"
        )},
        {"role": "system", "content": f"【课程内容片段】\n{markdown_content}"}
    ]
    
    # 追加历史记录
    for msg in history_messages:
        # 避免把刚才存进去的那条最新的 'user' message 重复加进去，
        # 因为我们会在下面显式加一条。
        # 简单的判断：如果 msg['content'] == request.message，可能误判。
        # 最好是 history 不包含最后一条。
        # 这里为了简化，我们直接把 history 全放进去，但要在 Service 里控制好，或者这里不手动加 user message?
        # 修正策略：既然 save_message 已经存了，get_conversation_history 就会把刚才那条也取出来。
        # 所以我们不需要再手动 append {"role": "user", "content": request.message} 了！
        # 直接把 history 喂给 AI 即可。
        messages_payload.append({"role": msg["role"], "content": msg["content"]})

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    if not api_key:
        async def missing_key_stream():
            yield "⚠️ 系统未配置 LLM API Key。\n请在后端环境变量中设置 `LLM_API_KEY`。"
        return StreamingResponse(missing_key_stream(), media_type="text/plain")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_stream():
        """
        生成流式响应
        注意：在异步生成器中使用独立的数据库会话，避免会话生命周期问题
        """
        db_stream = SessionLocal()
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=messages_payload,
                stream=True,
                temperature=0.7,
                max_tokens=2000
            )

            full_response_content = ""  # 用于收集完整回答

            # 先发一个 meta 信息给前端，告诉它 conversation_id
            # 注意：SSE (Server-Sent Events) 标准通常只发 data。
            # 为了简单，我们让前端自己处理，或者把 ID 放在第一个 chunk 里？
            # 更好的做法是：响应头里带 X-Conversation-Id。
            # 但这里是 StreamingResponse，头得在外面设。
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content_piece = chunk.choices[0].delta.content
                    full_response_content += content_piece
                    yield content_piece
            
            # 流式结束后，保存 AI 的回答到数据库
            # 使用独立的 db_stream 会话，确保在正确的上下文中保存
            LearningService.save_message(db_stream, conversation_id, "assistant", full_response_content)
            db_stream.commit()

        except Exception as e:
            yield f"\n\n❌ AI 服务调用失败: {str(e)}"
        finally:
            db_stream.close()
    
    response = StreamingResponse(generate_stream(), media_type="text/plain")
    # 在响应头中返回 conversation_id，这样前端下次可以带上它
    response.headers["X-Conversation-Id"] = conversation_id
    return response
