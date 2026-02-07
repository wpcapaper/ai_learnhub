"""
学习课程服务
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from app.models import Course, Chapter, ReadingProgress


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

        result = {
            "id": chapter.id,
            "course_id": chapter.course_id,
            "title": chapter.title,
            "content_markdown": chapter.content_markdown,
            "sort_order": chapter.sort_order,
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
