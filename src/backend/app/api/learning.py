"""
学习课程API
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Course, Chapter
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

    [开发说明] 这是一个预埋的 AI 助手接口，目前返回固定格式的响应。
    本函数作为后续接入真实 AI 模型（如 OpenAI GPT、DeepSeek 等）的基础框架。

    [当前输出格式]
    当前正在学习的章节ID为:{章节id}
    当前章节markdown为:{markdown内容，截断前50个字符}
    阿巴阿巴

    [开发指南]
    1. 如需接入真实 AI 模型，请参考以下步骤：
       - 在此函数中调用 AI 模型的 API（如 OpenAI、DeepSeek 等）
       - 将章节内容（chapter.content_markdown）作为上下文传递给 AI
       - 将用户的 request.message 作为问题传递给 AI
       - 处理 AI 的返回结果，保持流式响应格式

    2. 需要考虑的功能增强：
       - 添加用户对话历史记录（实现多轮对话）
       - 实现章节内容的语义检索（RAG）
       - 添加知识库增强（基于课程内容构建向量数据库）

    3. 数据库交互说明：
       - 通过 db: Session = Depends(get_db) 获取数据库会话
       - 通过 chapter_id 查询 Chapter 模型获取章节内容
       - Chapter.content_markdown 字段包含完整的 markdown 格式内容

    Args:
        request: 对话请求对象
            - chapter_id (str): 章节 ID，用于获取当前学习的章节内容
            - message (str): 用户的消息/问题
            - user_id (Optional[str]): 用户 ID，用于个性化或记录对话历史
        db: 数据库会话（通过依赖注入自动获取）

    Returns:
        StreamingResponse: 流式响应对象，模拟 AI 打字效果

    Raises:
        HTTPException 400: 当请求参数不合法时（章节 ID 或消息内容为空）
        HTTPException 404: 当指定的章节不存在于数据库时

    Example:
        >>> request = ChatRequest(
        ...     chapter_id="550e8400-e29b-41d4-a716-446655440000",
        ...     message="请解释一下这一章的核心概念"
        ... )
        >>> response = await ai_chat(request, db)
    """
    # 参数验证
    if not request.chapter_id:
        raise HTTPException(status_code=400, detail="章节 ID 不能为空")
    if not request.message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    # 从数据库查询章节信息
    # 注意：这里需要查询到章节的 markdown 内容，后续可以将此内容传递给 AI 模型
    chapter = db.query(Chapter).filter(
        Chapter.id == request.chapter_id,
        Chapter.is_deleted == False
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail=f"章节 {request.chapter_id} 不存在")

    # 获取章节内容并截断前 50 个字符（仅用于演示，后续可传递完整内容给 AI）
    # 注意：chapter.content_markdown 是实际字符串值，不是 Column 对象
    markdown_content = chapter.content_markdown
    markdown_preview = markdown_content[:50] if markdown_content else ""

    async def generate_stream():
        """
        生成流式响应

        [开发说明] 当前实现：
        - 返回章节信息和固定回复"阿巴阿巴"
        - 模拟流式输出效果（每个字符间隔 50ms）

        [后续修改建议]
        - 替换为调用真实 AI 模型 API
        - 将 chapter.content_markdown 作为上下文传递给 AI
        - 将 request.message 作为用户问题传递给 AI
        - 保持流式返回格式，逐字符或逐块输出 AI 响应
        """
        # 构建响应文本
        # 格式：章节ID信息 + Markdown预览 + 固定回复
        response_text = (
            f"当前正在学习的章节ID为:{chapter.id}\n"
            f"当前章节markdown为:\n"
            f"```markdown\n{markdown_preview}...\n```\n"
            f"\n\n🤖：阿巴阿巴"
        )

        # 模拟流式输出，每个字符间隔 50ms
        # [开发说明] 这是为了模拟 AI 打字效果的预埋实现
        # 后续可替换为真实的 AI 流式输出
        for char in response_text:
            yield char
            await asyncio.sleep(0.05)

    # 返回流式响应
    return StreamingResponse(generate_stream(), media_type="text/plain")
