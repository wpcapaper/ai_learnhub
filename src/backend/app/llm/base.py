"""
LLM 客户端抽象基类

定义 LLM 服务的统一接口，支持流式和非流式调用。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections.abc import AsyncGenerator
from enum import Enum


class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """
    聊天消息
    
    Attributes:
        role: 消息角色
        content: 消息内容
        name: 可选的发送者名称
    """
    role: MessageRole
    content: str
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式（用于 API 调用）"""
        result = {"role": self.role.value, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class ChatResponse:
    """
    非流式聊天响应
    
    Attributes:
        content: 响应内容
        model: 使用的模型名称
        usage: Token 使用情况
        finish_reason: 完成原因
    """
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


@dataclass  
class StreamChunk:
    """
    流式响应块
    
    Attributes:
        content: 内容片段
        finish_reason: 完成原因（最后一个块）
    """
    content: str
    finish_reason: Optional[str] = None


class LLMClient(ABC):
    """
    LLM 客户端抽象基类
    
    所有 LLM 实现都需要继承此类并实现抽象方法。
    提供统一的聊天接口，支持流式和非流式调用。
    """
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """
        非流式聊天
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称，为 None 时使用默认模型
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成 Token 数
            **kwargs: 其他模型参数
        
        Returns:
            ChatResponse 响应对象
        
        Raises:
            LLMError: LLM 调用失败时抛出
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        流式聊天（用于 SSE 场景）
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 Token 数
            **kwargs: 其他模型参数
        
        Yields:
            StreamChunk 流式响应块
        
        Raises:
            LLMError: LLM 调用失败时抛出
        """
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """获取默认模型名称"""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """检查客户端是否可用（配置是否正确）"""
        pass


class LLMError(Exception):
    """LLM 调用异常"""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        self.message = message
        self.cause = cause
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message
