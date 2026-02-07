"""
阅读进度模型 - 记录用户阅读进度
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class ReadingProgress(Base):
    """阅读进度模型 - 记录用户阅读进度"""

    __tablename__ = "reading_progress"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)  # 用户ID
    chapter_id = Column(String(36), ForeignKey('chapters.id'), nullable=False, index=True)  # 章节ID
    last_position = Column(Integer, default=0)  # 阅读位置（字符偏移量）
    last_percentage = Column(Float, default=0.0)  # 阅读百分比（0-100）
    is_completed = Column(Boolean, default=False)  # 是否完成
    last_read_at = Column(DateTime, default=datetime.utcnow)  # 最后阅读时间
    total_read_time = Column(Integer, default=0)  # 总阅读时长（秒）

    # 关系
    user = relationship("User", backref="reading_progresses")

    def __repr__(self):
        return f"<ReadingProgress(id='{self.id}' user_id='{self.user_id}' chapter_id='{self.chapter_id}' progress={self.last_percentage}%)>"
