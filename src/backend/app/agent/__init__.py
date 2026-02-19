"""
Agent 模块

提供基于 Skills 的智能体框架，支持流式输出。

使用示例:
    from app.agent import Agent, skill, AgentEvent
    
    class MyAgent(Agent):
        @skill("analyze")
        def analyze_data(self, data):
            return {"result": "analyzed"}
    
    agent = MyAgent()
    async for event in agent.run("分析这些数据"):
        print(event)
"""

from .base import (
    Agent,
    AgentContext,
    AgentResult,
    SkillRegistry,
    skill,
)
from .events import (
    AgentEvent,
    EventType,
    EventEncoder,
)
from .rag_optimizer import RAGOptimizerAgent

__all__ = [
    # 核心类
    "Agent",
    "AgentContext",
    "AgentResult",
    "AgentEvent",
    "EventType",
    "EventEncoder",
    "SkillRegistry",
    
    # 装饰器
    "skill",
    
    # 具体实现
    "RAGOptimizerAgent",
]
