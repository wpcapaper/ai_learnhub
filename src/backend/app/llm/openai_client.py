"""
OpenAI 兼容客户端实现

支持 OpenAI 及其兼容接口（如 DeepSeek、Azure OpenAI 等）。
"""

from typing import List, Dict, Optional, AsyncGenerator
import logging

from .base import (
    LLMClient,
    ChatResponse,
    StreamChunk,
    LLMError,
)
from .config import LLMConfig

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """
    OpenAI 兼容客户端
    
    支持所有 OpenAI 兼容的 API 服务，包括：
    - OpenAI 官方
    - DeepSeek
    - Azure OpenAI
    - 本地部署的兼容服务
    
    使用示例:
        config = LLMConfig(
            api_key="sk-xxx",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat"
        )
        client = OpenAIClient(config)
        
        # 非流式调用
        response = await client.chat([{"role": "user", "content": "Hello"}])
        print(response.content)
        
        # 流式调用
        async for chunk in client.chat_stream([{"role": "user", "content": "Hello"}]):
            print(chunk.content, end="")
    """
    
    def __init__(self, config: LLMConfig):
        """
        初始化 OpenAI 客户端
        
        Args:
            config: LLM 配置对象
        """
        self._config = config
        self._client = None
        self._async_client = None
    
    def _get_sync_client(self):
        """获取同步客户端（延迟初始化）"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=self._config.timeout,
                max_retries=self._config.max_retries,
            )
        return self._client
    
    def _get_async_client(self):
        """获取异步客户端（延迟初始化）"""
        if self._async_client is None:
            from openai import AsyncOpenAI
            self._async_client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=self._config.timeout,
                max_retries=self._config.max_retries,
            )
        return self._async_client
    
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
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 Token 数
            **kwargs: 其他参数（如 top_p, presence_penalty 等）
        
        Returns:
            ChatResponse 响应对象
        
        Raises:
            LLMError: API 调用失败时抛出
        """
        client = self._get_async_client()
        model = model or self._config.model
        
        # 构建请求参数
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        
        # 添加其他参数
        params.update(kwargs)
        
        try:
            # 调用 API
            response = await client.chat.completions.create(**params)
            
            # 构建响应
            return ChatResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
                finish_reason=response.choices[0].finish_reason,
            )
        
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise LLMError(f"LLM 调用失败: {str(e)}", cause=e)
    
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
            max_tokens: 最大 Token 数
            **kwargs: 其他参数
        
        Yields:
            StreamChunk 流式响应块
        
        Raises:
            LLMError: API 调用失败时抛出
        """
        client = self._get_async_client()
        model = model or self._config.model
        
        # 构建请求参数
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},  # 启用 usage 返回
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        
        params.update(kwargs)
        
        try:
            # 调用流式 API
            stream = await client.chat.completions.create(**params)
            
            # 逐块返回
            async for chunk in stream:
                # 检查是否有 usage 信息（最后一个块）
                if hasattr(chunk, 'usage') and chunk.usage:
                    yield StreamChunk(
                        content="",
                        finish_reason=None,
                        usage={
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        },
                    )
                # 检查是否有内容
                elif chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(
                        content=chunk.choices[0].delta.content,
                        finish_reason=chunk.choices[0].finish_reason,
                    )
                elif chunk.choices and chunk.choices[0].finish_reason:
                    # 只有 finish_reason 的块
                    yield StreamChunk(
                        content="",
                        finish_reason=chunk.choices[0].finish_reason,
                    )
        
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise LLMError(f"LLM 流式调用失败: {str(e)}", cause=e)
    
    @property
    def default_model(self) -> str:
        """获取默认模型名称"""
        return self._config.model
    
    @property
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return bool(self._config.api_key)
