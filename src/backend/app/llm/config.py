"""
LLM 配置管理模块

统一管理 LLM 服务的配置，支持环境变量和配置文件。
配置优先级：环境变量 > 默认值
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """
    LLM 服务配置
    
    Attributes:
        api_key: API 密钥
        base_url: API 基础地址（支持 OpenAI 兼容接口）
        model: 默认使用的模型名称
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
    """
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-3.5-turbo"
    timeout: float = 60.0
    max_retries: int = 3


@dataclass
class LangfuseConfig:
    """
    Langfuse 监控配置
    
    Attributes:
        public_key: Langfuse 公钥
        secret_key: Langfuse 私钥
        host: Langfuse 服务地址（自托管或云端）
        enabled: 是否启用监控
    """
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: str = "https://cloud.langfuse.com"
    enabled: bool = False
    
    def is_valid(self) -> bool:
        """检查配置是否有效（启用时需要密钥）"""
        if not self.enabled:
            return True
        return bool(self.public_key and self.secret_key)


def get_llm_config() -> LLMConfig:
    """
    从环境变量获取 LLM 配置
    
    环境变量：
        LLM_API_KEY: API 密钥（必需）
        LLM_BASE_URL: API 基础地址
        LLM_MODEL: 默认模型名称
        LLM_TIMEOUT: 请求超时时间
        LLM_MAX_RETRIES: 最大重试次数
    
    Returns:
        LLMConfig 配置对象
    
    Raises:
        ValueError: 当 API Key 未配置时
    """
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM API Key 未配置，请设置 LLM_API_KEY 环境变量")
    
    return LLMConfig(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
        timeout=float(os.getenv("LLM_TIMEOUT", "60.0")),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
    )


def get_langfuse_config() -> LangfuseConfig:
    """
    从环境变量获取 Langfuse 配置
    
    环境变量：
        LANGFUSE_PUBLIC_KEY: Langfuse 公钥
        LANGFUSE_SECRET_KEY: Langfuse 私钥
        LANGFUSE_HOST: Langfuse 服务地址
        LANGFUSE_ENABLED: 是否启用（默认当密钥存在时启用）
    
    Returns:
        LangfuseConfig 配置对象
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    # 当密钥存在时默认启用，除非明确设置 LANGFUSE_ENABLED=false
    enabled_env = os.getenv("LANGFUSE_ENABLED", "").lower()
    if enabled_env == "false":
        enabled = False
    elif enabled_env == "true":
        enabled = True
    else:
        # 默认：密钥存在则启用
        enabled = bool(public_key and secret_key)
    
    return LangfuseConfig(
        public_key=public_key,
        secret_key=secret_key,
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        enabled=enabled,
    )
