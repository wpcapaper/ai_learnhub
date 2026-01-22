"""
课程服务
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Course, UserCourseProgress


class CourseService:
    """课程服务"""

    @staticmethod
    def get_courses(db: Session, active_only: bool = True) -> List[Course]:
        """
        获取课程列表

        Args:
            db: 数据库会话
            active_only: 是否只返回启用的课程

        Returns:
            List[Course]: 课程列表
        """
        query = db.query(Course).filter(Course.is_deleted == False)

        if active_only:
            query = query.filter(Course.is_active == True)

        courses = query.order_by(Course.sort_order.asc(), Course.created_at.desc()).all()
        return courses

    @staticmethod
    def get_course_by_id(db: Session, course_id: str) -> Optional[Course]:
        """
        根据ID获取课程

        Args:
            db: 数据库会话
            course_id: 课程ID

        Returns:
            Optional[Course]: 课程对象
        """
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.is_deleted == False
        ).first()

        return course

    @staticmethod
    def get_course_by_code(db: Session, code: str) -> Optional[Course]:
        """
        根据代码获取课程

        Args:
            db: 数据库会话
            code: 课程代码

        Returns:
            Optional[Course]: 课程对象
        """
        course = db.query(Course).filter(
            Course.code == code,
            Course.is_deleted == False
        ).first()

        return course

    @staticmethod
    def get_course_with_progress(
        db: Session,
        course_id: str,
        user_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        获取课程信息及其用户进度（含轮次信息）

        Args:
            db: 数据库会话
            course_id: 课程ID
            user_id: 用户ID（可选，用于返回用户进度）

        Returns:
            Optional[dict]: 包含课程信息和用户进度的字典
        """
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.is_deleted == False
        ).first()

        if not course:
            return None

        result = {
            "id": course.id,
            "code": course.code,
            "title": course.title,
            "description": course.description,
            "course_type": course.course_type,
            "cover_image": course.cover_image,
            "default_exam_config": course.default_exam_config,
            "is_active": course.is_active,
            "sort_order": course.sort_order,
            "created_at": course.created_at.isoformat() if course.created_at else None
        }

        # 如果提供了用户ID，添加用户进度信息
        if user_id:
            progress = db.query(UserCourseProgress).filter(
                UserCourseProgress.user_id == user_id,
                UserCourseProgress.course_id == course_id
            ).first()

            if progress:
                result["current_round"] = progress.current_round
                result["total_rounds_completed"] = progress.total_rounds_completed

        return result
