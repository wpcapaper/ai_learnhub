"""
LLM 封装模块

提供统一的 LLM 调用接口和 Langfuse 监控功能。

使用示例:
    from app.llm import get_llm_client, trace_llm_call
    
    # 获取 LLM 客户端
    llm = get_llm_client()
    
    # 非流式调用
    response = await llm.chat([
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"}
    ])
    print(response.content)
    
    # 流式调用（用于 SSE）
    async for chunk in llm.chat_stream(messages):
        yield chunk.content
    
    # 使用 Langfuse 追踪
    @trace_llm_call("ai_chat", tags=["assistant"])
    async def my_chat_function(messages):
        return await llm.chat(messages)
"""

from typing import Optional

from .base import (
    LLMClient,
    ChatResponse,
    ChatMessage,
    StreamChunk,
    LLMError,
    MessageRole,
)
from .config import (
    LLMConfig,
    LangfuseConfig,
    get_llm_config,
    get_langfuse_config,
)
from .openai_client import OpenAIClient
from .langfuse_wrapper import (
    trace_llm_call,
    trace_embedding_call,
    trace_rerank_call,
    is_langfuse_enabled,
    reset_langfuse_client,
)


# 全局 LLM 客户端实例（延迟初始化）
_llm_client: Optional[LLMClient] = None


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """
    获取 LLM 客户端实例（单例模式）
    
    如果未提供配置，则从环境变量自动加载。
    
    Args:
        config: LLM 配置对象，为 None 时自动加载
    
    Returns:
        LLMClient 客户端实例
    
    Raises:
        ValueError: 当 API Key 未配置时
    """
    global _llm_client
    
    if _llm_client is not None and config is None:
        return _llm_client
    
    if config is None:
        config = get_llm_config()
    
    # 目前只支持 OpenAI 兼容客户端，未来可扩展
    _llm_client = OpenAIClient(config)
    
    return _llm_client


def reset_llm_client():
    """重置 LLM 客户端（用于测试或重新配置）"""
    global _llm_client
    _llm_client = None


# 导出的公共接口
__all__ = [
    # 客户端
    "LLMClient",
    "OpenAIClient",
    "get_llm_client",
    "reset_llm_client",
    
    # 数据类
    "ChatResponse",
    "ChatMessage",
    "StreamChunk",
    "LLMError",
    "MessageRole",
    
    # 配置
    "LLMConfig",
    "LangfuseConfig",
    "get_llm_config",
    "get_langfuse_config",
    
    # Langfuse 监控
    "trace_llm_call",
    "trace_embedding_call",
    "trace_rerank_call",
    "is_langfuse_enabled",
    "reset_langfuse_client",
]
