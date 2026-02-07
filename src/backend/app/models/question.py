"""
题目模型（激进版 - 0-1阶段）
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class Question(Base):
    """题目模型（激进版 - 0-1阶段）"""
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, index=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False, index=True)
    question_type = Column(String(20), nullable=False, index=True)  # single_choice | multiple_choice | true_false
    content = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # {"A": "...", "B": "...", ...}
    correct_answer = Column(String(10), nullable=False, index=True)
    explanation = Column(Text, nullable=True)
    knowledge_points = Column(JSON, nullable=True)  # ["监督学习", "分类"]
    difficulty = Column(Integer, default=2, nullable=True)  # 1-5
    question_set_ids = Column(JSON, nullable=True, default=list)  # 记录题目所属的固定题集
    is_controversial = Column(Boolean, default=False)
    extra_data = Column(JSON, default={})
    vector_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # 关系
    course = relationship("Course", back_populates="questions")
    records = relationship("UserLearningRecord", back_populates="question")

    def __repr__(self):
        return f"<Question(id='{self.id}' type='{self.question_type}' content='{self.content[:30]}...')>"
