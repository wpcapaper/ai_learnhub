"""
用户答题历史模型
记录用户每次的答题情况，保留完整历史
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class UserAnswerHistory(Base):
    """
    用户答题历史记录（每次答题都创建新记录，永不更新）

    设计原则：
    - 每次答题都创建新记录，从不更新
    - is_correct 字段固定不变，记录当时的答案状态
    - 用于追踪"历史上做错过"的题目
    """
    __tablename__ = "user_answer_history"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False, index=True)
    answer = Column(String(10), nullable=False)  # 用户答案（固定不变）
    is_correct = Column(Boolean, nullable=False)  # 是否正确（固定不变）
    answered_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)  # 答题时间
    review_stage = Column(Integer, nullable=False)  # 答题时的复习阶段
    batch_id = Column(String(36), ForeignKey("quiz_batches.id"), nullable=True, index=True)  # 关联批次（可选）

    # 关系
    user = relationship("User")
    question = relationship("Question")
    batch = relationship("QuizBatch")

    def __repr__(self):
        return f"<AnswerHistory(id='{self.id}' user='{self.user_id}' qid='{self.question_id}' correct={self.is_correct} at={self.answered_at})>"
