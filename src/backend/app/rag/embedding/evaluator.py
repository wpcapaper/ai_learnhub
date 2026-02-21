"""Embedding模型评估工具"""

from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
import numpy as np
from dataclasses import dataclass

from .models import EmbeddingModel

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class TestQuery:
    """测试查询"""
    query: str
    relevant_chunk_ids: List[str]  # 相关chunk的ID列表


@dataclass
class TestSet:
    """测试集"""
    queries: List[TestQuery]
    chunks: Dict[str, str]  # chunk_id -> chunk_text


@dataclass
class TestResult:
    """测试结果"""
    query: str
    retrieved_chunk_ids: List[str]
    relevant_chunk_ids: List[str]
    top_k: int
    recall_at_k: float
    precision_at_k: float
    mrr: float  # Mean Reciprocal Rank


@dataclass
class TestReport:
    """测试报告"""
    model_name: str
    results: List[TestResult]
    avg_recall_at_k: Dict[int, float]  # k -> recall
    avg_precision_at_k: Dict[int, float]  # k -> precision
    avg_mrr: float


class EmbeddingEvaluator:
    """Embedding模型评估器"""
    
    def __init__(self, embedding_model: EmbeddingModel):
        """
        Args:
            embedding_model: Embedding模型
        """
        self.model = embedding_model
    
    def evaluate_recall(
        self,
        test_set: TestSet,
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> TestReport:
        """
        评估召回率
        
        Args:
            test_set: 测试集
            top_k: Top K召回
            similarity_threshold: 相似度阈值
        
        Returns:
            测试报告
        """
        results = []
        
        # 编码所有chunks
        chunk_ids = list(test_set.chunks.keys())
        chunk_texts = [test_set.chunks[cid] for cid in chunk_ids]
        chunk_embeddings = self.model.encode(chunk_texts)
        
        # 评估每个查询
        for test_query in test_set.queries:
            # 编码查询
            query_embedding = self.model.encode([test_query.query])[0]
            
            # 计算相似度
            similarities = np.dot(chunk_embeddings, query_embedding)
            
            # 获取Top K
            top_indices = np.argsort(similarities)[::-1][:top_k]
            retrieved_chunk_ids = [chunk_ids[i] for i in top_indices]
            
            # 过滤相似度阈值
            if similarity_threshold > 0:
                retrieved_chunk_ids = [
                    cid for i, cid in enumerate(retrieved_chunk_ids)
                    if similarities[top_indices[i]] >= similarity_threshold
                ]
            
            # 计算指标
            relevant_set = set(test_query.relevant_chunk_ids)
            retrieved_set = set(retrieved_chunk_ids)
            
            # 计算不同K值的指标
            recall_at_k = {}
            precision_at_k = {}
            mrr = 0.0
            
            for k in range(1, top_k + 1):
                retrieved_k = set(retrieved_chunk_ids[:k])
                relevant_k = relevant_set & retrieved_k
                
                recall = len(relevant_k) / len(relevant_set) if relevant_set else 0.0
                precision = len(relevant_k) / k if k > 0 else 0.0
                
                recall_at_k[k] = recall
                precision_at_k[k] = precision
                
                # MRR: 第一个相关结果的倒数排名
                if mrr == 0.0:
                    for rank, cid in enumerate(retrieved_chunk_ids[:k], 1):
                        if cid in relevant_set:
                            mrr = 1.0 / rank
                            break
            
            result = TestResult(
                query=test_query.query,
                retrieved_chunk_ids=retrieved_chunk_ids,
                relevant_chunk_ids=test_query.relevant_chunk_ids,
                top_k=top_k,
                recall_at_k=recall_at_k.get(top_k, 0.0),
                precision_at_k=precision_at_k.get(top_k, 0.0),
                mrr=mrr
            )
            results.append(result)
        
        # 计算平均指标
        avg_recall_at_k = {}
        avg_precision_at_k = {}
        avg_mrr = 0.0
        
        for k in range(1, top_k + 1):
            recalls = [r.recall_at_k.get(k, 0.0) for r in results]
            precisions = [r.precision_at_k.get(k, 0.0) for r in results]
            avg_recall_at_k[k] = np.mean(recalls) if recalls else 0.0
            avg_precision_at_k[k] = np.mean(precisions) if precisions else 0.0
        
        avg_mrr = np.mean([r.mrr for r in results]) if results else 0.0
        
        return TestReport(
            model_name=self.model.get_model_name(),
            results=results,
            avg_recall_at_k=avg_recall_at_k,
            avg_precision_at_k=avg_precision_at_k,
            avg_mrr=avg_mrr
        )
    
    def compare_models(
        self,
        models: List[EmbeddingModel],
        test_set: TestSet,
        top_k: int = 5
    ):
        """
        对比多个模型
        
        Args:
            models: 模型列表
            test_set: 测试集
            top_k: Top K
        
        Returns:
            对比结果DataFrame
        """
        import pandas as pd
        
        results = []
        
        for model in models:
            evaluator = EmbeddingEvaluator(model)
            report = evaluator.evaluate_recall(test_set, top_k)
            
            results.append({
                "model": model.get_model_name(),
                "avg_recall@1": report.avg_recall_at_k.get(1, 0.0),
                "avg_recall@3": report.avg_recall_at_k.get(3, 0.0),
                "avg_recall@5": report.avg_recall_at_k.get(5, 0.0),
                "avg_precision@5": report.avg_precision_at_k.get(5, 0.0),
                "avg_mrr": report.avg_mrr,
            })
        
        return pd.DataFrame(results)
