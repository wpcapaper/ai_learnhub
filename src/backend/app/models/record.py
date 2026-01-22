"""
用户学习记录模型（调整版 - 艾宾浩斯逻辑调整）
记录用户答题历史和复习状态
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class UserLearningRecord(Base):
    """
    用户学习记录（调整版 - 艾宾浩斯逻辑调整）
    记录用户答题历史和复习状态

    字段说明：
    - review_stage, next_review_time, completed_in_current_round: 正在使用（艾宾浩斯算法）
    """
    __tablename__ = "user_learning_records"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False, index=True)
    review_stage = Column(Integer, default=0, index=True)  # 0-7, 8=MASTERED - 当前复习阶段
    next_review_time = Column(DateTime, index=True, nullable=True)  # 可为空（答对的题不在艾宾浩斯曲线中）- 下次复习时间
    completed_in_current_round = Column(Boolean, default=False, index=True)  # 在当前轮次是否刷过（独立于艾宾浩斯状态）- 轮次管理

    # 关系
    question = relationship("Question", back_populates="records")

    def __repr__(self):
        return f"<Record(id='{self.id}' user='{self.user_id}' qid='{self.question_id}' stage={self.review_stage})>"
