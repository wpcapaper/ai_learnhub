"""
Agent 基类和 Skills 框架

提供基于装饰器的 Skills 注册机制和 Agent 执行框架。
"""

import asyncio
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Generator, AsyncGenerator
from functools import wraps
from datetime import datetime

from .events import AgentEvent, EventType


# ============== Skill Registry ==============

class SkillRegistry:
    """
    Skill 注册表
    
    管理所有注册的 skills 及其元数据。
    """
    
    _instance: Optional["SkillRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: Dict[str, Dict[str, Any]] = {}
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置注册表（用于测试）"""
        cls._instance = None
    
    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        params: Optional[Dict[str, Any]] = None,
    ):
        """注册一个 skill"""
        self._skills[name] = {
            "name": name,
            "func": func,
            "description": description or func.__doc__ or "",
            "params": params or {},
        }
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """获取 skill 信息"""
        return self._skills.get(name)
    
    def get_func(self, name: str) -> Optional[Callable]:
        """获取 skill 函数"""
        skill_info = self._skills.get(name)
        return skill_info["func"] if skill_info else None
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有 skills"""
        return [
            {
                "name": info["name"],
                "description": info["description"],
                "params": info["params"],
            }
            for info in self._skills.values()
        ]


def skill(
    name: str,
    description: str = "",
    params: Optional[Dict[str, Any]] = None,
):
    """
    Skill 装饰器
    
    将方法注册为 Agent 可调用的 skill。
    
    使用示例:
        class MyAgent(Agent):
            @skill("analyze", description="分析数据", params={"data": "输入数据"})
            def analyze_data(self, data: str) -> dict:
                return {"result": "analyzed"}
    
    Args:
        name: Skill 名称
        description: Skill 描述
        params: 参数说明
    """
    def decorator(func: Callable) -> Callable:
        # 注册到全局注册表
        registry = SkillRegistry()
        registry.register(name, func, description, params)
        
        # 添加元数据
        func._is_skill = True
        func._skill_name = name
        func._skill_description = description
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # 保留元数据
        wrapper._is_skill = True
        wrapper._skill_name = name
        wrapper._skill_description = description
        
        return wrapper
    
    return decorator


# ============== Agent Context ==============

@dataclass
class AgentContext:
    """
    Agent 执行上下文
    
    存储执行过程中的状态和数据。
    """
    task_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    
    def set_variable(self, key: str, value: Any):
        """设置变量"""
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)
    
    def add_result(self, skill: str, output: Any, duration_ms: float = 0):
        """添加 skill 执行结果"""
        self.results.append({
            "skill": skill,
            "output": output,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        })


# ============== Agent Result ==============

@dataclass
class AgentResult:
    """
    Agent 执行结果
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


# ============== Base Agent ==============

class Agent(ABC):
    """
    Agent 基类
    
    提供基于 Skills 的智能体框架。子类需要实现 `execute` 方法。
    
    使用示例:
        class MyAgent(Agent):
            @skill("greet")
            def greet(self, name: str) -> str:
                return f"Hello, {name}!"
            
            async def execute(self, context: AgentContext) -> AsyncGenerator[AgentEvent, None]:
                yield AgentEvent.agent_start("Starting...")
                result = await self.call_skill("greet", name="World")
                yield AgentEvent.skill_output("greet", result)
                yield AgentEvent.agent_complete("Done!")
    """
    
    def __init__(self):
        self._registry = SkillRegistry()
        self._register_instance_skills()
    
    def _register_instance_skills(self):
        """注册实例上的 skills"""
        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr) and getattr(attr, "_is_skill", False):
                skill_name = getattr(attr, "_skill_name", name)
                # 绑定到实例
                self._registry.register(
                    skill_name,
                    attr,
                    getattr(attr, "_skill_description", ""),
                )
    
    @property
    def skills(self) -> List[Dict[str, Any]]:
        """获取所有可用 skills"""
        return self._registry.list_skills()
    
    async def call_skill(
        self,
        name: str,
        **kwargs
    ) -> Any:
        """
        调用 skill
        
        Args:
            name: Skill 名称
            **kwargs: 传递给 skill 的参数
        
        Returns:
            Skill 执行结果
        """
        func = self._registry.get_func(name)
        if func is None:
            raise ValueError(f"Unknown skill: {name}")
        
        # 支持同步和异步函数
        if asyncio.iscoroutinefunction(func):
            return await func(**kwargs)
        else:
            return func(**kwargs)
    
    @abstractmethod
    async def execute(
        self,
        context: AgentContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行 Agent 逻辑（子类实现）
        
        Args:
            context: 执行上下文
        
        Yields:
            执行过程中的事件
        """
        pass
    
    def run(
        self,
        task_id: str,
        **input_data
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        运行 Agent
        
        Args:
            task_id: 任务 ID
            **input_data: 输入数据
        
        Yields:
            执行过程中的事件
        """
        context = AgentContext(
            task_id=task_id,
            input_data=input_data,
        )
        return self.execute(context)
    
    async def run_to_completion(
        self,
        task_id: str,
        **input_data
    ) -> AgentResult:
        """
        运行 Agent 直到完成
        
        Args:
            task_id: 任务 ID
            **input_data: 输入数据
        
        Returns:
            最终结果
        """
        start_time = datetime.now()
        final_data = None
        error = None
        
        try:
            async for event in self.run(task_id, **input_data):
                if event.type == EventType.AGENT_COMPLETE:
                    final_data = event.data
                elif event.type == EventType.AGENT_ERROR:
                    error = event.data.get("error") if event.data else event.content
        except Exception as e:
            error = str(e)
        
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        return AgentResult(
            success=error is None,
            message="执行完成" if error is None else f"执行失败: {error}",
            data=final_data,
            error=error,
            duration_ms=duration_ms,
        )
