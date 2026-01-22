"""
用户模型
支持Dev模式（免注册）和生产模式
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100), nullable=True)
    is_temp_user = Column(Boolean, default=False)
    total_study_time = Column(Integer, default=0)
    user_level = Column(String(20), nullable=True)  # 'beginner' | 'intermediate' | 'advanced'
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_deleted = Column(Boolean, default=False)

    # 关系
    batches = relationship("QuizBatch", back_populates="user")

    def __repr__(self):
        return f"<User(id='{self.id}' username='{self.username}' nickname='{self.nickname}') is_temp_user={self.is_temp_user}>"
