"""
课程模型（激进版 - 含默认配置）
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    course_type = Column(String(20), nullable=False, index=True)
    cover_image = Column(String(500), nullable=True)

    default_exam_config = Column(JSON, nullable=True, default=None)

    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    questions = relationship("Question", back_populates="course")
    question_sets = relationship("QuestionSet", backref="course")

    def __repr__(self):
        return f"<Course(id='{self.id}' code='{self.code}' title='{self.title}')>"
