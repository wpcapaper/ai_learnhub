from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .base import Base

class Conversation(Base):
    """AI 对话会话模型"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # 暂时允许为空，直到接入完整 Auth
    chapter_id = Column(String(36), ForeignKey("chapters.id"), nullable=False)
    
    # 自动生成的会话摘要（用于历史列表展示）
    summary = Column(String(200), nullable=True)
    
    # 元数据（预留扩展，如 tags, context_tokens 等）
    meta_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    user = relationship("User", backref="conversations")
    chapter = relationship("Chapter", backref="conversations")

class Message(Base):
    """AI 对话消息模型"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    
    # 消息角色: 'user', 'assistant', 'system'
    role = Column(String(20), nullable=False)
    
    # 消息内容
    content = Column(Text, nullable=False)
    
    # Token 消耗统计（可选）
    token_usage = Column(JSON, nullable=True)
    
    # 用户反馈: 'like', 'dislike', None
    rating = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    conversation = relationship("Conversation", back_populates="messages")