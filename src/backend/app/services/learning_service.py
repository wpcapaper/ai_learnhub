"""
学习课程服务
"""
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path
from sqlalchemy.orm import Session

from app.models import Course, Chapter, ReadingProgress, Conversation, Message


# 获取 courses 目录路径（支持 Docker 和本地环境）
def _get_courses_dir() -> Path:
    docker_path = Path("/app/courses")
    if docker_path.exists():
        return docker_path
    return Path(__file__).parent.parent.parent.parent.parent / "courses"


class LearningService:
    """学习课程服务"""

    @staticmethod
    def get_chapters(db: Session, course_id: str) -> List[Chapter]:
        """
        获取指定课程的所有章节列表

        Args:
            db: 数据库会话
            course_id: 课程 ID

        Returns:
            List[Chapter]: 按排序顺序排列的章节列表

        Raises:
            ValueError: 当课程不存在时抛出异常
        """
        # 验证课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError(f"课程 {course_id} 不存在")

        # 查询课程的所有章节，按排序顺序返回
        chapters = db.query(Chapter).filter(
            Chapter.course_id == course_id,
            Chapter.is_deleted == False
        ).order_by(Chapter.sort_order.asc()).all()

        return chapters

    @staticmethod
    def get_chapter_content(
        db: Session,
        user_id: Optional[str],
        chapter_id: str
    ) -> Dict:
        """
        获取章节内容，如果提供了用户 ID，则同时返回用户的阅读进度

        Args:
            db: 数据库会话
            user_id: 用户 ID（可选）
            chapter_id: 章节 ID

        Returns:
            Dict: 包含章节内容和用户进度的字典

        Raises:
            ValueError: 当章节不存在时抛出异常
        """
        # 查询章节
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.is_deleted == False
        ).first()

        if not chapter:
            raise ValueError(f"章节 {chapter_id} 不存在")

        # 查询课程信息，获取 course.code
        course = db.query(Course).filter(Course.id == chapter.course_id).first()
        course_code = course.code if course else ""

        # 查找课程目录名（course_code 可能与目录名不同）
        course_dir_name = ""
        file_path = ""
        courses_dir = _get_courses_dir()
        
        # 遍历 courses 目录，找到包含匹配 course.json 的目录
        if courses_dir.exists():
            for course_dir in courses_dir.iterdir():
                if not course_dir.is_dir():
                    continue
                course_json_path = course_dir / "course.json"
                if not course_json_path.exists():
                    continue
                try:
                    with open(course_json_path, 'r', encoding='utf-8') as f:
                        course_json = json.load(f)
                    # 根据 code 匹配
                    if course_json.get("code") == course_code:
                        course_dir_name = course_dir.name
                        # 同时读取章节文件路径
                        chapters_info = course_json.get("chapters", [])
                        for ch_info in chapters_info:
                            if ch_info.get("sort_order") == chapter.sort_order:
                                file_path = ch_info.get("file", "")
                                break
                        break
                except:
                    pass

        result = {
            "id": chapter.id,
            "course_id": chapter.course_id,
            "title": chapter.title,
            "content_markdown": chapter.content_markdown,
            "sort_order": chapter.sort_order,
            "course_code": course_code,
            "course_dir_name": course_dir_name,
            "file_path": file_path,
        }

        # 如果提供了用户 ID，查询用户的阅读进度
        if user_id:
            progress = db.query(ReadingProgress).filter(
                ReadingProgress.user_id == user_id,
                ReadingProgress.chapter_id == chapter_id
            ).first()

            if progress:
                result["user_progress"] = {
                    "last_position": progress.last_position,
                    "last_percentage": progress.last_percentage,
                    "is_completed": progress.is_completed,
                    "last_read_at": progress.last_read_at.isoformat() if progress.last_read_at else None,
                    "total_read_time": progress.total_read_time,
                }
            else:
                result["user_progress"] = {
                    "last_position": 0,
                    "last_percentage": 0.0,
                    "is_completed": False,
                    "last_read_at": None,
                    "total_read_time": 0,
                }

        return result

    @staticmethod
    def update_reading_progress(
        db: Session,
        user_id: str,
        chapter_id: str,
        position: int,
        percentage: float
    ) -> ReadingProgress:
        """
        更新用户的阅读进度

        Args:
            db: 数据库会话
            user_id: 用户 ID
            chapter_id: 章节 ID
            position: 阅读位置（字符偏移量）
            percentage: 阅读百分比（0-100）

        Returns:
            ReadingProgress: 更新后的阅读进度对象

        Raises:
            ValueError: 当章节不存在时抛出异常
        """
        # 验证章节是否存在
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.is_deleted == False
        ).first()

        if not chapter:
            raise ValueError(f"章节 {chapter_id} 不存在")

        # 查询或创建阅读进度记录
        progress = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == user_id,
            ReadingProgress.chapter_id == chapter_id
        ).first()

        if progress:
            # 更新现有进度
            progress.last_position = position
            progress.last_percentage = percentage
            progress.last_read_at = datetime.utcnow()  # 需要导入 datetime
            db.commit()
            db.refresh(progress)
        else:
            # 创建新的进度记录
            progress = ReadingProgress(
                id=str(uuid.uuid4()),  # 需要导入 uuid
                user_id=user_id,
                chapter_id=chapter_id,
                last_position=position,
                last_percentage=percentage,
                last_read_at=datetime.utcnow()
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)

        return progress

    @staticmethod
    def mark_chapter_completed(
        db: Session,
        user_id: str,
        chapter_id: str
    ) -> ReadingProgress:
        """
        标记章节为已完成

        Args:
            db: 数据库会话
            user_id: 用户 ID
            chapter_id: 章节 ID

        Returns:
            ReadingProgress: 更新后的阅读进度对象

        Raises:
            ValueError: 当章节不存在时抛出异常
        """
        # 验证章节是否存在
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.is_deleted == False
        ).first()

        if not chapter:
            raise ValueError(f"章节 {chapter_id} 不存在")

        # 查询或创建阅读进度记录
        progress = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == user_id,
            ReadingProgress.chapter_id == chapter_id
        ).first()

        if progress:
            # 更新现有进度
            progress.is_completed = True
            progress.last_percentage = 100.0
            progress.last_read_at = datetime.utcnow()
            db.commit()
            db.refresh(progress)
        else:
            # 创建新的进度记录并标记为完成
            progress = ReadingProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                chapter_id=chapter_id,
                last_position=0,
                last_percentage=100.0,
                is_completed=True,
                last_read_at=datetime.utcnow()
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)

        return progress

    @staticmethod
    def get_user_progress_summary(
        db: Session,
        user_id: str,
        course_id: str
    ) -> Dict:
        """
        获取用户在指定课程中的学习进度摘要

        Args:
            db: 数据库会话
            user_id: 用户 ID
            course_id: 课程 ID

        Returns:
            Dict: 包含课程进度信息的字典

        Raises:
            ValueError: 当课程不存在时抛出异常
        """
        # 验证课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError(f"课程 {course_id} 不存在")

        # 获取课程的所有章节
        chapters = db.query(Chapter).filter(
            Chapter.course_id == course_id,
            Chapter.is_deleted == False
        ).all()

        total_chapters = len(chapters)
        completed_count = 0
        total_percentage = 0.0

        # 统计完成情况和平均进度
        for chapter in chapters:
            progress = db.query(ReadingProgress).filter(
                ReadingProgress.user_id == user_id,
                ReadingProgress.chapter_id == chapter.id
            ).first()

            if progress:
                if progress.is_completed:
                    completed_count += 1
                    total_percentage += 100.0
                else:
                    total_percentage += progress.last_percentage
            else:
                total_percentage += 0.0

        # 计算平均进度
        average_percentage = total_percentage / total_chapters if total_chapters > 0 else 0.0

        result = {
            "course_id": course_id,
            "course_title": course.title,
            "total_chapters": total_chapters,
            "completed_chapters": completed_count,
            "progress_percentage": average_percentage,
        }

        return result

    @staticmethod
    def create_conversation(db: Session, user_id: Optional[str], chapter_id: str) -> Conversation:
        """
        创建一个新的对话会话
        """
        conversation = Conversation(
            user_id=user_id,
            chapter_id=chapter_id,
            summary="新对话"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_conversation_history(db: Session, conversation_id: str, limit: int = 10) -> List[Dict]:
        """
        获取对话历史消息
        """
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        # 因为是按时间倒序查的（为了取最近 N 条），返回前要反转回来，变成正序
        return [
            {"role": msg.role, "content": msg.content} 
            for msg in reversed(messages)
        ]

    @staticmethod
    def save_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
        """
        保存一条消息
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
