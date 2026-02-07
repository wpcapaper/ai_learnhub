"""
用户设置服务（Phase 1：数据模型支持）
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models import Course, UserSettings
import secrets


class UserSettingsService:
    """用户设置服务（Phase 1：数据模型支持）"""

    @staticmethod
    def get_user_settings(db: Session, user_id: str) -> Optional[UserSettings]:
        """
        获取用户设置

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Optional[UserSettings]: 用户设置对象
        """
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()

        return settings

    @staticmethod
    def get_exam_config(
        db: Session,
        user_id: str,
        course_id: str
    ) -> Dict[str, any]:
        """
        获取考试配置（配置优先级逻辑）

        优先级：用户设置 > 课程默认 > 硬编码

        Args:
            db: 数据库会话
            user_id: 用户ID
            course_id: 课程ID

        Returns:
            Dict: 考试配置
            {
                "question_type_config": {
                    "single_choice": 30,
                    "multiple_choice": 10,
                    "true_false": 10
                },
                "difficulty_range": [1, 5]
            }
        """
        # 1. 硬编码默认值（最低优先级）
        default_config = {
            "question_type_config": {
                "single_choice": 30,
                "multiple_choice": 10,
                "true_false": 10
            },
            "difficulty_range": [1, 5]
        }

        # 2. 课程默认配置（中等优先级）
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.is_deleted == False
        ).first()

        if course and course.default_exam_config:
            # 合并课程配置
            for key in default_config:
                if key in course.default_exam_config:
                    default_config[key] = course.default_exam_config[key]

        # 3. 用户设置（最高优先级）
        user_settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()

        if user_settings and user_settings.course_settings:
            course_config = user_settings.course_settings.get(course_id, {})
            if "exam_config" in course_config:
                user_exam_config = course_config["exam_config"]

                # 合并用户配置
                for key in default_config:
                    if key in user_exam_config:
                        if isinstance(default_config[key], dict):
                            # 合并嵌套字典
                            for sub_key in default_config[key]:
                                if sub_key in user_exam_config[key]:
                                    default_config[key][sub_key] = user_exam_config[key][sub_key]
                        else:
                            default_config[key] = user_exam_config[key]

        return default_config

    @staticmethod
    def ensure_user_settings(db: Session, user_id: str) -> UserSettings:
        """
        确保用户设置存在（如果不存在则创建）

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            UserSettings: 用户设置对象
        """
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()

        if not settings:
            settings = UserSettings(
                id=secrets.token_hex(16),
                user_id=user_id,
                course_settings={}
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return settings
