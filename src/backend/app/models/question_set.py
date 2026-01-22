"""
题集模型（激进版 - 只保留固定题集）
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class QuestionSet(Base):
    """题集模型（激进版 - 只保留固定题集）"""
    __tablename__ = "question_sets"

    id = Column(String(36), primary_key=True, index=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)  # 题集代码
    name = Column(String(200), nullable=False)  # 题集名称

    # 固定题集字段
    fixed_question_ids = Column(JSON, nullable=False)  # 固定题集的题目ID列表

    description = Column(Text, nullable=True)  # 题集描述
    total_questions = Column(Integer, default=0)  # 题目总数
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    def __repr__(self):
        return f"<QuestionSet(code='{self.code}' name='{self.name}')>"
