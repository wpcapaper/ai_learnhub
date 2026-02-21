from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os
import httpx
import logging

logger = logging.getLogger(__name__)


class EmbeddingModel(ABC):
    @abstractmethod
    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        pass


class OpenAIEmbedder(EmbeddingModel):
    """调用 OpenAI 或兼容 API 的 Embedding 服务"""
    
    def __init__(self, model: str, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        
        # 根据模型确定维度
        self._dimension_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        self._dimension = self._dimension_map.get(model, 1536)
    
    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        """调用 OpenAI API 生成向量"""
        return self._encode_with_tracing(texts)
    
    def _encode_with_tracing(self, texts: List[str]) -> List[List[float]]:
        """带 Langfuse 追踪的编码实现"""
        from app.llm.langfuse_wrapper import _get_langfuse_client
        from datetime import datetime as dt
        
        langfuse_client = _get_langfuse_client()
        trace = None
        start_time = dt.now()
        
        # 准备 trace 输入数据
        input_data = {
            "text_count": len(texts),
            "model": self.model,
            "sample": texts[0][:100] if texts else None,
        }
        
        if langfuse_client:
            trace = langfuse_client.trace(
                name="openai_embedding",
                input=input_data,
                tags=["embedding", "openai"],
            )
        
        error_occurred = None
        result = None
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": texts,
                        "model": self.model,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                embeddings = sorted(data["data"], key=lambda x: x["index"])
                result = [item["embedding"] for item in embeddings]
                return result
                
        except httpx.HTTPStatusError as e:
            error_occurred = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            raise RuntimeError(f"Embedding API 调用失败: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            error_occurred = str(e)
            raise RuntimeError(f"Embedding API 调用异常: {str(e)}")
        finally:
            # 记录 trace 到 Langfuse
            if langfuse_client and trace:
                end_time = dt.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                output_data: Dict[str, Any] = {
                    "embedding_count": len(result) if result else 0,
                    "dimension": len(result[0]) if result else 0,
                }
                
                if error_occurred:
                    output_data["error"] = error_occurred
                
                trace.span(
                    name="embedding_call",
                    input=input_data,
                    output=output_data,
                    start_time=start_time,
                    end_time=end_time,
                    metadata={"duration_ms": duration_ms, "model": self.model},
                )
                
                trace.update(output=output_data)
                langfuse_client.flush()
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_model_name(self) -> str:
        return self.model


class OllamaEmbedder(EmbeddingModel):
    """Ollama Embedding 服务"""
    
    def __init__(self, endpoint: str, model: str = "nomic-embed-text", dimension: int = 768, timeout: int = 60):
        self.endpoint = endpoint
        self.model = model
        self._dimension = dimension
        self.timeout = timeout
    
    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        embeddings = []
        
        with httpx.Client(timeout=self.timeout) as client:
            for text in texts:
                response = client.post(
                    self.endpoint,
                    json={"model": self.model, "prompt": text}
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
        
        return embeddings
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_model_name(self) -> str:
        return f"ollama/{self.model}"


class RemoteEmbedder(EmbeddingModel):
    """调用本地/远程 Embedding 服务（如 Ollama、vLLM、自建服务）"""
    
    def __init__(self, endpoint: str, dimension: int = 1024, model_name: str = "custom", timeout: int = 30, api_key: Optional[str] = None):
        self.endpoint = endpoint
        self._dimension = dimension
        self._model_name = model_name
        self.timeout = timeout
        self.api_key = api_key
    
    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        """调用远程服务生成向量"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.endpoint,
                    headers=headers,
                    json={"texts": texts},
                )
                response.raise_for_status()
                data = response.json()
                
                # 支持多种响应格式
                if isinstance(data, list):
                    return data
                elif "embeddings" in data:
                    return data["embeddings"]
                elif "data" in data:
                    # OpenAI 兼容格式
                    return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
                else:
                    raise ValueError(f"未知的响应格式: {list(data.keys())}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Embedding 服务调用失败: {e.response.status_code}")
        except Exception as e:
            raise RuntimeError(f"Embedding 服务调用异常: {str(e)}")
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_model_name(self) -> str:
        return self._model_name


class EmbeddingModelFactory:
    """根据配置创建 Embedding 客户端"""
    
    # OpenAI 模型配置
    OPENAI_MODELS = {
        "text-embedding-3-small": {"dimension": 1536, "description": "OpenAI 小模型，性价比高"},
        "text-embedding-3-large": {"dimension": 3072, "description": "OpenAI 大模型，性能最好"},
        "text-embedding-ada-002": {"dimension": 1536, "description": "OpenAI 旧版模型"},
    }
    
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> EmbeddingModel:
        """
        从配置字典创建 Embedding 客户端
        
        配置格式示例:
        {
            "provider": "openai",  # openai | local | custom
            "openai": {
                "model": "text-embedding-3-small",
                "api_key": "sk-xxx",
                "base_url": "https://api.openai.com/v1"
            },
            "local": {
                "endpoint": "http://localhost:11434/api/embeddings",
                "model": "nomic-embed-text",
                "timeout": 30
            }
        }
        """
        provider = config.get("provider", "openai")
        
        if provider == "openai":
            openai_config = config.get("openai", {})
            api_key = openai_config.get("api_key") or os.getenv("RAG_OPENAI_API_KEY")
            if not api_key:
                raise ValueError("RAG Embedding未配置，请设置 RAG_OPENAI_API_KEY 环境变量")
            
            return OpenAIEmbedder(
                model=openai_config.get("model", "text-embedding-3-small"),
                api_key=api_key,
                base_url=openai_config.get("base_url", "https://api.openai.com/v1"),
            )
        
        elif provider == "local":
            local_config = config.get("local", {})
            endpoint = local_config.get("endpoint") or os.getenv("RAG_EMBEDDING_SERVICE_URL")
            if not endpoint:
                raise ValueError("RAG本地Embedding服务地址未配置，请设置 RAG_EMBEDDING_SERVICE_URL 环境变量")
            
            model_name = local_config.get("model", "nomic-embed-text")
            
            # Ollama 使用 /api/embeddings 端点
            if "/api/embeddings" in endpoint:
                return OllamaEmbedder(
                    endpoint=endpoint,
                    model=model_name,
                    dimension=local_config.get("dimension", 1024),
                    timeout=local_config.get("timeout", 60),
                )
            
            return RemoteEmbedder(
                endpoint=endpoint,
                dimension=local_config.get("dimension", 768),
                model_name=model_name,
                timeout=local_config.get("timeout", 30),
            )
        
        elif provider == "custom":
            custom_config = config.get("custom", {})
            endpoint = custom_config.get("endpoint") or os.getenv("RAG_EMBEDDING_ENDPOINT")
            if not endpoint:
                raise ValueError("RAG自定义Embedding服务地址未配置，请设置 RAG_EMBEDDING_ENDPOINT 环境变量")
            
            return RemoteEmbedder(
                endpoint=endpoint,
                dimension=custom_config.get("dimension", 1024),
                model_name=custom_config.get("model_name", "custom-embedding"),
                timeout=custom_config.get("timeout", 30),
                api_key=custom_config.get("api_key") or os.getenv("RAG_EMBEDDING_API_KEY"),
            )
        
        else:
            raise ValueError(f"不支持的 Embedding provider: {provider}")
    
    @classmethod
    def list_models(cls) -> List[dict]:
        """列出 OpenAI 可用模型"""
        return [
            {
                "key": key,
                "name": key,
                "description": info["description"],
                "dimension": info["dimension"],
            }
            for key, info in cls.OPENAI_MODELS.items()
        ]
