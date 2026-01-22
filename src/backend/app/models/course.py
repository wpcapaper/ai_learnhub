"""
课程模型（激进版 - 含默认配置）
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class Course(Base):
    """课程模型（激进版 - 含默认配置）"""
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 课程代码
    title = Column(String(200), nullable=False)  # 课程标题
    description = Column(Text)  # 课程描述
    course_type = Column(String(20), nullable=False, index=True)  # exam | learning
    cover_image = Column(String(500), nullable=True)  # 封面图URL

    # 默认考试配置（系统级）
    default_exam_config = Column(JSON, nullable=True, default={
        "question_type_config": {
            "single_choice": 30,
            "multiple_choice": 10,
            "true_false": 10
        },
        "difficulty_range": [1, 5]
    })

    is_active = Column(Boolean, default=True)  # 是否启用
    sort_order = Column(Integer, default=0)  # 排序
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # 关系
    questions = relationship("Question", back_populates="course")
    question_sets = relationship("QuestionSet", backref="course")

    def __repr__(self):
        return f"<Course(id='{self.id}' code='{self.code}' title='{self.title}')>"
