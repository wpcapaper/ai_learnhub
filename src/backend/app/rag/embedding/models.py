from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os
import httpx


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
                
                # 按 index 排序确保顺序正确
                embeddings = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in embeddings]
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Embedding API 调用失败: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Embedding API 调用异常: {str(e)}")
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_model_name(self) -> str:
        return self.model


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
                "endpoint": "http://localhost:8001/embed",
                "timeout": 30
            }
        }
        """
        provider = config.get("provider", "openai")
        
        if provider == "openai":
            openai_config = config.get("openai", {})
            api_key = openai_config.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API Key 未配置，请设置 OPENAI_API_KEY 环境变量")
            
            return OpenAIEmbedder(
                model=openai_config.get("model", "text-embedding-3-small"),
                api_key=api_key,
                base_url=openai_config.get("base_url", "https://api.openai.com/v1"),
            )
        
        elif provider == "local":
            local_config = config.get("local", {})
            endpoint = local_config.get("endpoint") or os.getenv("EMBEDDING_SERVICE_URL")
            if not endpoint:
                raise ValueError("本地 Embedding 服务地址未配置，请设置 EMBEDDING_SERVICE_URL 环境变量")
            
            return RemoteEmbedder(
                endpoint=endpoint,
                dimension=local_config.get("dimension", 1024),
                model_name=local_config.get("model_name", "local-embedding"),
                timeout=local_config.get("timeout", 30),
            )
        
        elif provider == "custom":
            custom_config = config.get("custom", {})
            endpoint = custom_config.get("endpoint") or os.getenv("EMBEDDING_ENDPOINT")
            if not endpoint:
                raise ValueError("自定义 Embedding 服务地址未配置，请设置 EMBEDDING_ENDPOINT 环境变量")
            
            return RemoteEmbedder(
                endpoint=endpoint,
                dimension=custom_config.get("dimension", 1024),
                model_name=custom_config.get("model_name", "custom-embedding"),
                timeout=custom_config.get("timeout", 30),
                api_key=custom_config.get("api_key") or os.getenv("EMBEDDING_API_KEY"),
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
