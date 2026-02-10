"""召回测试工具"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import os

from ..retrieval.retriever import RAGRetriever
from .metrics import calculate_recall, calculate_precision, calculate_mrr


@dataclass
class TestCase:
    """测试用例"""
    query: str
    relevant_chunk_ids: List[str]


@dataclass
class TestResult:
    """单个测试结果"""
    query: str
    retrieved_chunk_ids: List[str]
    relevant_chunk_ids: List[str]
    recall_at_k: Dict[int, float]  # k -> recall
    precision_at_k: Dict[int, float]  # k -> precision
    mrr: float


@dataclass
class TestReport:
    """测试报告"""
    total_queries: int
    results: List[TestResult]
    avg_recall_at_k: Dict[int, float]
    avg_precision_at_k: Dict[int, float]
    avg_mrr: float


class RecallTester:
    """召回测试工具"""
    
    def __init__(self, retriever: RAGRetriever):
        """
        Args:
            retriever: RAG检索器
        """
        self.retriever = retriever
    
    async def run_test(
        self,
        test_cases: List[TestCase],
        course_id: str,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> TestReport:
        """
        运行召回测试
        
        Args:
            test_cases: 测试用例列表
            course_id: 课程ID
            top_k: Top K召回
            score_threshold: 相似度阈值
        
        Returns:
            测试报告
        """
        results = []
        
        for test_case in test_cases:
            # 执行检索
            retrieval_results = await self.retriever.retrieve(
                query=test_case.query,
                course_id=course_id,
                top_k=top_k,
                score_threshold=score_threshold
            )
            
            retrieved_chunk_ids = [r.chunk_id for r in retrieval_results]
            relevant_set = set(test_case.relevant_chunk_ids)
            
            # 计算不同K值的指标
            recall_at_k = {}
            precision_at_k = {}
            
            for k in range(1, top_k + 1):
                retrieved_k = set(retrieved_chunk_ids[:k])
                
                recall = calculate_recall(retrieved_k, relevant_set)
                precision = calculate_precision(retrieved_k, relevant_set)
                
                recall_at_k[k] = recall
                precision_at_k[k] = precision
            
            # 计算MRR
            mrr = calculate_mrr(retrieved_chunk_ids, relevant_set)
            
            result = TestResult(
                query=test_case.query,
                retrieved_chunk_ids=retrieved_chunk_ids,
                relevant_chunk_ids=test_case.relevant_chunk_ids,
                recall_at_k=recall_at_k,
                precision_at_k=precision_at_k,
                mrr=mrr
            )
            results.append(result)
        
        # 计算平均指标
        avg_recall_at_k = {}
        avg_precision_at_k = {}
        avg_mrr = 0.0
        
        if results:
            for k in range(1, top_k + 1):
                recalls = [r.recall_at_k.get(k, 0.0) for r in results]
                precisions = [r.precision_at_k.get(k, 0.0) for r in results]
                
                avg_recall_at_k[k] = sum(recalls) / len(recalls)
                avg_precision_at_k[k] = sum(precisions) / len(precisions)
            
            avg_mrr = sum(r.mrr for r in results) / len(results)
        
        return TestReport(
            total_queries=len(test_cases),
            results=results,
            avg_recall_at_k=avg_recall_at_k,
            avg_precision_at_k=avg_precision_at_k,
            avg_mrr=avg_mrr
        )
    
    def generate_report(self, report: TestReport, output_file: Optional[str] = None) -> str:
        """
        生成测试报告
        
        Args:
            report: 测试报告
            output_file: 输出文件路径（可选）
        
        Returns:
            报告字符串
        """
        lines = []
        lines.append("=" * 60)
        lines.append("RAG召回测试报告")
        lines.append("=" * 60)
        lines.append(f"\n总查询数: {report.total_queries}")
        lines.append(f"\n平均MRR: {report.avg_mrr:.4f}")
        lines.append("\n平均召回率 (Recall@K):")
        for k, recall in sorted(report.avg_recall_at_k.items()):
            lines.append(f"  Recall@{k}: {recall:.4f}")
        
        lines.append("\n平均精确率 (Precision@K):")
        for k, precision in sorted(report.avg_precision_at_k.items()):
            lines.append(f"  Precision@{k}: {precision:.4f}")
        
        lines.append("\n" + "=" * 60)
        lines.append("详细结果:")
        lines.append("=" * 60)
        
        for i, result in enumerate(report.results, 1):
            lines.append(f"\n查询 {i}: {result.query}")
            lines.append(f"  相关chunk IDs: {result.relevant_chunk_ids}")
            lines.append(f"  检索到chunk IDs: {result.retrieved_chunk_ids}")
            lines.append(f"  MRR: {result.mrr:.4f}")
            lines.append("  召回率:")
            for k, recall in sorted(result.recall_at_k.items()):
                lines.append(f"    Recall@{k}: {recall:.4f}")
        
        report_text = "\n".join(lines)
        
        # 保存到文件
        if output_file:
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_text)
        
        return report_text
    
    @staticmethod
    def load_test_cases_from_json(file_path: str) -> List[TestCase]:
        """
        从JSON文件加载测试用例
        
        JSON格式:
        [
            {
                "query": "问题文本",
                "relevant_chunk_ids": ["chunk_id1", "chunk_id2"]
            },
            ...
        ]
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return [TestCase(**item) for item in data]
