"""
章节模型 - 学习课程的章节信息
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class Chapter(Base):
    """章节模型 - 学习课程的章节信息"""

    __tablename__ = "chapters"

    id = Column(String(36), primary_key=True, index=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False, index=True)  # 所属课程ID
    code = Column(String(100), nullable=True, index=True)  # 章节唯一标识（课程内），如 "introduction"
    title = Column(String(200), nullable=False)  # 章节标题
    content_markdown = Column(Text, nullable=False)  # Markdown内容
    sort_order = Column(Integer, default=0)  # 章节排序
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    is_deleted = Column(Boolean, default=False)  # 是否删除

    # 关系
    course = relationship("Course", backref="chapters")
    reading_progresses = relationship("ReadingProgress", backref="chapter")

    def __repr__(self):
        return f"<Chapter(id='{self.id}' code='{self.code}' title='{self.title}' course_id='{self.course_id}')>"
