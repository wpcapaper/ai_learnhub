"""Embedding模型封装"""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingModel(ABC):
    """Embedding模型抽象基类"""
    
    @abstractmethod
    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """
        编码文本为向量
        
        Args:
            texts: 文本列表
            **kwargs: 其他参数
        
        Returns:
            向量数组 (n_samples, dim)
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """获取向量维度"""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称"""
        pass


class SentenceTransformerModel(EmbeddingModel):
    """基于sentence-transformers的模型"""
    
    def __init__(self, model_name: str, device: Optional[str] = None):
        """
        Args:
            model_name: 模型名称或路径
            device: 设备（'cuda', 'cpu'等），None表示自动选择
        """
        self.model_name = model_name
        self._model = SentenceTransformer(model_name, device=device)
        self._dimension = self._model.get_sentence_embedding_dimension()
    
    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """编码文本"""
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=kwargs.get("normalize", True),
            show_progress_bar=kwargs.get("show_progress", False),
            batch_size=kwargs.get("batch_size", 32)
        )
        return embeddings
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return self._dimension
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.model_name


class EmbeddingModelFactory:
    """Embedding模型工厂"""
    
    # 支持的模型配置
    MODEL_CONFIGS = {
        "text2vec-base-chinese": {
            "name": "shibing624/text2vec-base-chinese",
            "description": "中文基础模型，轻量级",
            "dimension": 768,
        },
        "bge-large-zh": {
            "name": "BAAI/bge-large-zh-v1.5",
            "description": "中文大模型，性能优秀",
            "dimension": 1024,
        },
        "multilingual-e5-large": {
            "name": "intfloat/multilingual-e5-large",
            "description": "多语言模型，支持中英文",
            "dimension": 1024,
        },
        "bge-small-zh": {
            "name": "BAAI/bge-small-zh-v1.5",
            "description": "中文小模型，速度快",
            "dimension": 512,
        },
    }
    
    @classmethod
    def create(
        cls,
        model_key: str,
        device: Optional[str] = None
    ) -> EmbeddingModel:
        """
        创建Embedding模型
        
        Args:
            model_key: 模型键名（如 'text2vec-base-chinese'）
            device: 设备
        
        Returns:
            EmbeddingModel实例
        """
        if model_key not in cls.MODEL_CONFIGS:
            raise ValueError(
                f"Unknown model key: {model_key}. "
                f"Available: {list(cls.MODEL_CONFIGS.keys())}"
            )
        
        config = cls.MODEL_CONFIGS[model_key]
        model_name = config["name"]
        
        return SentenceTransformerModel(model_name, device=device)
    
    @classmethod
    def list_models(cls) -> List[dict]:
        """列出所有可用模型"""
        return [
            {
                "key": key,
                "name": config["name"],
                "description": config["description"],
                "dimension": config["dimension"],
            }
            for key, config in cls.MODEL_CONFIGS.items()
        ]
