"""
Agent 事件定义

定义 Agent 执行过程中产生的事件类型，用于流式输出。
"""

import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from datetime import datetime


class EventType(str, Enum):
    """事件类型枚举"""
    
    # Agent 生命周期
    AGENT_START = "agent_start"         # Agent 开始执行
    AGENT_THINKING = "agent_thinking"   # Agent 思考中
    AGENT_COMPLETE = "agent_complete"   # Agent 执行完成
    AGENT_ERROR = "agent_error"         # Agent 执行错误
    
    # Skill 执行
    SKILL_START = "skill_start"         # Skill 开始执行
    SKILL_OUTPUT = "skill_output"       # Skill 输出内容
    SKILL_COMPLETE = "skill_complete"   # Skill 执行完成
    SKILL_ERROR = "skill_error"         # Skill 执行错误
    
    # 结果输出
    RESULT = "result"                   # 最终结果
    PROGRESS = "progress"               # 进度更新
    
    # 调试信息
    DEBUG = "debug"                     # 调试信息
    LOG = "log"                         # 日志信息


@dataclass
class AgentEvent:
    """
    Agent 事件
    
    用于流式输出 Agent 执行过程中的各种信息。
    
    Attributes:
        type: 事件类型
        content: 事件内容
        skill: 当前执行的 skill 名称（可选）
        data: 额外数据（可选）
        timestamp: 事件时间戳
    """
    type: EventType
    content: str
    skill: Optional[str] = None
    data: Optional[dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.skill:
            result["skill"] = self.skill
        if self.data:
            result["data"] = self.data
        return result
    
    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        return f"data: {json.dumps(self.to_dict(), ensure_ascii=False)}\n\n"
    
    @classmethod
    def agent_start(cls, content: str) -> "AgentEvent":
        """创建 Agent 开始事件"""
        return cls(type=EventType.AGENT_START, content=content)
    
    @classmethod
    def agent_thinking(cls, content: str) -> "AgentEvent":
        """创建 Agent 思考事件"""
        return cls(type=EventType.AGENT_THINKING, content=content)
    
    @classmethod
    def agent_complete(cls, content: str, data: Optional[dict] = None) -> "AgentEvent":
        """创建 Agent 完成事件"""
        return cls(type=EventType.AGENT_COMPLETE, content=content, data=data)
    
    @classmethod
    def agent_error(cls, content: str, error: Optional[str] = None) -> "AgentEvent":
        """创建 Agent 错误事件"""
        return cls(type=EventType.AGENT_ERROR, content=content, data={"error": error} if error else None)
    
    @classmethod
    def skill_start(cls, skill: str, content: str) -> "AgentEvent":
        """创建 Skill 开始事件"""
        return cls(type=EventType.SKILL_START, skill=skill, content=content)
    
    @classmethod
    def skill_output(cls, skill: str, content: str, data: Optional[dict] = None) -> "AgentEvent":
        """创建 Skill 输出事件"""
        return cls(type=EventType.SKILL_OUTPUT, skill=skill, content=content, data=data)
    
    @classmethod
    def skill_complete(cls, skill: str, content: str, data: Optional[dict] = None) -> "AgentEvent":
        """创建 Skill 完成事件"""
        return cls(type=EventType.SKILL_COMPLETE, skill=skill, content=content, data=data)
    
    @classmethod
    def skill_error(cls, skill: str, content: str, error: Optional[str] = None) -> "AgentEvent":
        """创建 Skill 错误事件"""
        return cls(type=EventType.SKILL_ERROR, skill=skill, content=content, data={"error": error} if error else None)
    
    @classmethod
    def result(cls, content: str, data: Optional[dict] = None) -> "AgentEvent":
        """创建结果事件"""
        return cls(type=EventType.RESULT, content=content, data=data)
    
    @classmethod
    def progress(cls, current: int, total: int, message: str) -> "AgentEvent":
        """创建进度事件"""
        return cls(
            type=EventType.PROGRESS,
            content=message,
            data={"current": current, "total": total, "percent": round(current / total * 100, 1) if total > 0 else 0}
        )


class EventEncoder(json.JSONEncoder):
    """事件 JSON 编码器"""
    
    def default(self, obj):
        if isinstance(obj, AgentEvent):
            return obj.to_dict()
        if isinstance(obj, EventType):
            return obj.value
        return super().default(obj)
