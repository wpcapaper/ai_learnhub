"""
批次刷题模型
记录每次刷题会话
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class QuizBatch(Base):
    """批次刷题模型"""
    __tablename__ = "quiz_batches"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    batch_size = Column(Integer, default=10)  # 每批默认10题
    mode = Column(String(20), default="practice")  # practice | exam
    round_number = Column(Integer, default=1)  # 轮次编号，从1开始
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    status = Column(String(20), default="in_progress")  # in_progress | completed
    is_deleted = Column(Boolean, default=False)

    # 关系
    user = relationship("User", back_populates="batches")
    answers = relationship("BatchAnswer", back_populates="batch")

    def __repr__(self):
        return f"<Batch(id='{self.id}' mode='{self.mode}' user='{self.user_id}' status={self.status})>"


class BatchAnswer(Base):
    """批次答题记录"""
    __tablename__ = "batch_answers"

    id = Column(String(36), primary_key=True)
    batch_id = Column(String(36), ForeignKey("quiz_batches.id"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False, index=True)
    user_answer = Column(String(10))
    is_correct = Column(Boolean, nullable=True)  # 批次结束后统一更新
    answered_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    batch = relationship("QuizBatch", back_populates="answers")
    question = relationship("Question")

    def __repr__(self):
        return f"<BatchAnswer(id='{self.id}' batch='{self.batch_id}' qid='{self.question_id}' correct={self.is_correct})>"
