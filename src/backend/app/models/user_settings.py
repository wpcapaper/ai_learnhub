"""
用户设置模型（0-1阶段：课程相关设置）
"""
from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime

from .base import Base


class UserSettings(Base):
    """用户设置模型（0-1阶段：课程相关设置）"""
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True, unique=True)

    # 课程相关设置（JSON结构，灵活扩展）
    # 示例结构：
    # {
    #   "course-1": {
    #     "exam_config": {
    #       "question_type_config": {
    #         "single_choice": 20,
    #         "multiple_choice": 15,
    #         "true_false": 15
    #       },
    #       "difficulty_range": [2, 4]
    #     },
    #     "practice_mode": "sequential"
    #   }
    # }
    course_settings = Column(JSON, nullable=True, default={})

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserSettings(user_id='{self.user_id}')>"
