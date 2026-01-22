"""
用户课程进度模型
跟踪用户在每个课程上的进度和轮次信息
"""
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class UserCourseProgress(Base):
    """用户课程进度模型"""
    __tablename__ = "user_course_progress"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)  # 用户ID
    course_id = Column(String(36), nullable=False, index=True)  # 课程ID
    current_round = Column(Integer, default=1)  # 当前轮次，从1开始
    total_rounds_completed = Column(Integer, default=0)  # 已完成轮次数
    started_at = Column(DateTime, default=datetime.utcnow)  # 第一次开始时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 最后更新时间

    def __repr__(self):
        return f"<UserCourseProgress(user='{self.user_id}' course='{self.course_id}' round={self.current_round})>"
