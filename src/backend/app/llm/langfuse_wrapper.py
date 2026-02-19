"""
Langfuse 监控封装模块

提供 LLM/Embedding/Rerank 调用的监控追踪功能。
通过装饰器方式无侵入集成到现有代码。

兼容 Langfuse SDK v2.x
"""

import os
import logging
from functools import wraps
from typing import Optional, List, Dict, Any, Callable, TypeVar, ParamSpec
from datetime import datetime

from .config import LangfuseConfig, get_langfuse_config

logger = logging.getLogger(__name__)

# 类型变量用于装饰器
P = ParamSpec("P")
R = TypeVar("R")

# 全局 Langfuse 客户端（延迟初始化）
_langfuse_client = None
_langfuse_enabled = None


def _get_langfuse_client():
    """
    获取 Langfuse 客户端（延迟初始化）
    
    Returns:
        Langfuse 客户端实例，如果未配置则返回 None
    """
    global _langfuse_client, _langfuse_enabled
    
    # 已经确定不可用，直接返回
    if _langfuse_enabled is False:
        return None
    
    # 已经初始化成功
    if _langfuse_client is not None:
        return _langfuse_client
    
    config = get_langfuse_config()
    
    if not config.enabled or not config.is_valid():
        logger.debug("Langfuse 监控未启用或配置无效")
        _langfuse_enabled = False
        return None
    
    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=config.public_key,
            secret_key=config.secret_key,
            host=config.host,
        )
        _langfuse_enabled = True
        logger.info(f"Langfuse 客户端已初始化，地址: {config.host}")
        return _langfuse_client
    except ImportError:
        logger.warning("langfuse 未安装，监控功能不可用。请运行: pip install langfuse")
        _langfuse_enabled = False
        return None
    except Exception as e:
        logger.error(f"Langfuse 初始化失败: {e}")
        _langfuse_enabled = False
        return None


def reset_langfuse_client():
    """重置 Langfuse 客户端（用于测试或重新配置）"""
    global _langfuse_client, _langfuse_enabled
    _langfuse_client = None
    _langfuse_enabled = None


def trace_llm_call(
    name: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    """
    追踪 LLM 调用的装饰器
    
    自动记录 LLM 调用的输入、输出和耗时，并上报到 Langfuse。
    
    使用示例:
        @trace_llm_call("ai_chat", tags=["assistant", "course"])
        async def chat(messages: List[Dict], **kwargs):
            # LLM 调用逻辑
            return response
    
    Args:
        name: 追踪名称（在 Langfuse 中显示）
        metadata: 额外的元数据
        tags: 标签列表（用于过滤和分类）
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            client = _get_langfuse_client()
            
            # 如果 Langfuse 未启用，直接执行原函数
            if client is None:
                return await func(*args, **kwargs)
            
            # 记录开始时间
            start_time = datetime.now()
            
            # 提取输入信息（用于追踪）
            input_data = {
                "args": str(args)[:500] if args else None,
                "kwargs": {k: str(v)[:200] for k, v in kwargs.items()},
            }
            
            try:
                # 执行原函数
                result = await func(*args, **kwargs)
                
                # 计算耗时
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                # 提取输出信息
                output_data = None
                if hasattr(result, 'content'):
                    output_data = {"content": result.content[:500]}
                elif isinstance(result, str):
                    output_data = {"content": result[:500]}
                
                # v2 API: 使用 trace() 方法
                trace = client.trace(
                    name=name,
                    input=input_data,
                    output=output_data,
                    metadata=metadata or {},
                    tags=tags or [],
                )
                
                # 添加 Span 记录详细信息
                trace.span(
                    name=f"{name}_call",
                    input=input_data,
                    output=output_data,
                    start_time=start_time,
                    end_time=datetime.now(),
                    metadata={
                        "duration_ms": duration_ms,
                        **(metadata or {}),
                    },
                )
                
                # 刷新确保数据上报
                client.flush()
                
                return result
            
            except Exception as e:
                # 记录错误
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                client.trace(
                    name=name,
                    input=input_data,
                    output={"error": str(e)},
                    metadata={
                        "duration_ms": duration_ms,
                        "error": True,
                        **(metadata or {}),
                    },
                    tags=(tags or []) + ["error"],
                )
                client.flush()
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """同步函数包装器"""
            client = _get_langfuse_client()
            
            if client is None:
                return func(*args, **kwargs)
            
            start_time = datetime.now()
            input_data = {
                "args": str(args)[:500] if args else None,
                "kwargs": {k: str(v)[:200] for k, v in kwargs.items()},
            }
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                output_data = None
                if hasattr(result, 'content'):
                    output_data = {"content": result.content[:500]}
                elif isinstance(result, str):
                    output_data = {"content": result[:500]}
                
                # v2 API
                trace = client.trace(
                    name=name,
                    input=input_data,
                    output=output_data,
                    metadata=metadata or {},
                    tags=tags or [],
                )
                
                trace.span(
                    name=f"{name}_call",
                    input=input_data,
                    output=output_data,
                    start_time=start_time,
                    end_time=datetime.now(),
                )
                
                client.flush()
                return result
            
            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                client.trace(
                    name=name,
                    input=input_data,
                    output={"error": str(e)},
                    metadata={"duration_ms": duration_ms, "error": True},
                    tags=(tags or []) + ["error"],
                )
                client.flush()
                raise
        
        # 根据函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def trace_embedding_call(
    name: str = "embedding",
    *,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    """
    追踪 Embedding 调用的装饰器
    
    使用示例:
        @trace_embedding_call("course_embedding", tags=["rag"])
        def encode(texts: List[str]) -> List[List[float]]:
            return embeddings
    
    Args:
        name: 追踪名称
        metadata: 额外元数据
        tags: 标签列表
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            client = _get_langfuse_client()
            
            if client is None:
                return func(*args, **kwargs)
            
            start_time = datetime.now()
            
            # 提取文本数量信息
            texts = args[0] if args else kwargs.get('texts', [])
            input_data = {
                "text_count": len(texts) if isinstance(texts, list) else 1,
                "sample": str(texts[0])[:200] if texts else None,
            }
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                # 提取向量维度信息
                output_data = None
                if isinstance(result, list) and result:
                    output_data = {
                        "embedding_count": len(result),
                        "dimension": len(result[0]) if result[0] else 0,
                    }
                
                # v2 API
                client.trace(
                    name=name,
                    input=input_data,
                    output=output_data,
                    metadata={
                        "duration_ms": duration_ms,
                        **(metadata or {}),
                    },
                    tags=["embedding"] + (tags or []),
                )
                client.flush()
                
                return result
            
            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                client.trace(
                    name=name,
                    input=input_data,
                    output={"error": str(e)},
                    metadata={"duration_ms": duration_ms, "error": True},
                    tags=["embedding", "error"] + (tags or []),
                )
                client.flush()
                raise
        
        return wrapper
    
    return decorator


def trace_rerank_call(
    name: str = "rerank",
    *,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    """
    追踪 Rerank 调用的装饰器
    
    使用示例:
        @trace_rerank_call("search_rerank", tags=["rag"])
        def rerank(query: str, results: List) -> List:
            return reranked
    
    Args:
        name: 追踪名称
        metadata: 额外元数据
        tags: 标签列表
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            client = _get_langfuse_client()
            
            if client is None:
                return func(*args, **kwargs)
            
            start_time = datetime.now()
            
            input_data = {
                "query": kwargs.get('query', args[0] if args else None),
                "result_count": len(args[1]) if len(args) > 1 else 0,
            }
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                output_data = {
                    "reranked_count": len(result) if isinstance(result, list) else 1,
                }
                
                # v2 API
                client.trace(
                    name=name,
                    input=input_data,
                    output=output_data,
                    metadata={
                        "duration_ms": duration_ms,
                        **(metadata or {}),
                    },
                    tags=["rerank"] + (tags or []),
                )
                client.flush()
                
                return result
            
            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                client.trace(
                    name=name,
                    input=input_data,
                    output={"error": str(e)},
                    metadata={"duration_ms": duration_ms, "error": True},
                    tags=["rerank", "error"] + (tags or []),
                )
                client.flush()
                raise
        
        return wrapper
    
    return decorator


# 便捷函数：检查 Langfuse 是否可用
def is_langfuse_enabled() -> bool:
    """检查 Langfuse 监控是否启用且可用"""
    return _get_langfuse_client() is not None
