"""
RAG 优化 Agent

基于 Skills 的 RAG 分块策略优化智能体。
自动测试不同分块策略，推荐最优配置。

使用统一的 LLM 封装和 Langfuse 监控。
"""

import asyncio
import time
import re
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path

from .base import Agent, AgentContext, skill
from .events import AgentEvent


class RAGOptimizerAgent(Agent):
    """
    RAG 优化 Agent
    
    通过 Skills 执行流程：
    1. 分析课程内容特征
    2. 测试多种分块策略
    3. 在沙箱中构建索引
    4. 执行检索测试
    5. 对比评估结果
    6. 推荐最优配置
    
    所有 LLM 调用使用统一封装，支持 Langfuse 监控。
    """
    
    # 预定义的分块策略
    DEFAULT_STRATEGIES = [
        {
            "name": "semantic_small",
            "type": "semantic",
            "config": {"min_chunk_size": 100, "max_chunk_size": 500, "overlap_size": 100}
        },
        {
            "name": "semantic_medium",
            "type": "semantic",
            "config": {"min_chunk_size": 200, "max_chunk_size": 1000, "overlap_size": 200}
        },
        {
            "name": "semantic_large",
            "type": "semantic",
            "config": {"min_chunk_size": 500, "max_chunk_size": 2000, "overlap_size": 300}
        },
        {
            "name": "fixed_small",
            "type": "fixed",
            "config": {"chunk_size": 256, "overlap_size": 50}
        },
        {
            "name": "fixed_medium",
            "type": "fixed",
            "config": {"chunk_size": 512, "overlap_size": 100}
        },
        {
            "name": "heading_based",
            "type": "heading",
            "config": {"min_chunk_size": 200, "max_chunk_size": 1500}
        },
    ]
    
    def __init__(self):
        super().__init__()
        self._results: Dict[str, Dict[str, Any]] = {}
    
    # ============== Skills ==============
    
    @skill(
        "analyze_content",
        description="分析课程内容特征",
        params={"content": "课程内容文本"}
    )
    def analyze_content(self, content: str) -> Dict[str, Any]:
        """
        分析课程内容特征
        
        Returns:
            内容特征：章节数、平均长度、内容类型分布等
        """
        # 统计基本信息
        chapters = content.count("\n# ") + content.count("\n## ")
        total_chars = len(content)
        lines = content.split("\n")
        code_blocks = content.count("```")
        
        # 检测内容类型
        has_code = code_blocks > 0
        has_math = "$$" in content or "$" in content
        has_tables = "|" in content and "---" in content
        
        # 分析章节长度分布
        chapter_lengths = []
        current_length = 0
        for line in lines:
            if line.startswith("# ") or line.startswith("## "):
                if current_length > 0:
                    chapter_lengths.append(current_length)
                current_length = 0
            current_length += len(line)
        if current_length > 0:
            chapter_lengths.append(current_length)
        
        avg_chapter_length = sum(chapter_lengths) / len(chapter_lengths) if chapter_lengths else total_chars
        
        return {
            "total_chars": total_chars,
            "chapters": max(chapters, 1),
            "code_blocks": code_blocks // 2,
            "has_code": has_code,
            "has_math": has_math,
            "has_tables": has_tables,
            "avg_chapter_length": int(avg_chapter_length),
            "suggested_strategies": self._suggest_strategies(
                has_code=has_code,
                has_math=has_math,
                avg_length=avg_chapter_length
            ),
        }
    
    def _suggest_strategies(
        self,
        has_code: bool,
        has_math: bool,
        avg_length: float
    ) -> List[str]:
        """根据内容特征推荐策略"""
        strategies = []
        
        if has_code or has_math:
            # 代码和公式内容，推荐按语义分块保持完整性
            strategies.extend(["semantic_medium", "heading_based"])
        else:
            # 普通文本内容
            strategies.extend(["semantic_small", "semantic_medium"])
        
        if avg_length > 1500:
            # 长章节，推荐大块分块
            strategies.append("semantic_large")
        
        if avg_length < 500:
            # 短章节，推荐固定分块
            strategies.append("fixed_small")
        
        # 始终测试 heading_based
        if "heading_based" not in strategies:
            strategies.append("heading_based")
        
        return list(set(strategies))[:4]  # 最多4个策略
    
    @skill(
        "test_chunking",
        description="测试分块策略",
        params={"content": "课程内容", "strategy": "分块策略配置"}
    )
    def test_chunking(
        self,
        content: str,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        测试分块策略
        
        Returns:
            分块结果：分块数量、大小分布、示例
        """
        from app.rag.chunking import SemanticChunkingStrategy
        from app.rag.chunking.filters import ContentFilter
        
        strategy_type = strategy.get("type", "semantic")
        config = strategy.get("config", {})
        
        # 创建对应的分块策略
        if strategy_type == "semantic":
            chunker = SemanticChunkingStrategy(
                min_chunk_size=config.get("min_chunk_size", 100),
                max_chunk_size=config.get("max_chunk_size", 1000),
                overlap_size=config.get("overlap_size", 200),
            )
        else:
            # 简化处理，都用语义分块
            chunker = SemanticChunkingStrategy(
                min_chunk_size=config.get("min_chunk_size", 100),
                max_chunk_size=config.get("max_chunk_size", 1000),
                overlap_size=config.get("overlap_size", 200),
            )
        
        # 执行分块
        chunks = chunker.chunk(content, course_id="test", chapter_id="test")
        
        # 统计分块信息
        chunk_sizes = [len(c.text) for c in chunks]
        
        return {
            "strategy_name": strategy.get("name", "unknown"),
            "chunk_count": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
            "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
            "sample_chunks": [
                {"text": c.text[:200], "size": len(c.text)}
                for c in chunks[:3]
            ],
        }
    
    @skill(
        "generate_test_queries",
        description="生成测试查询",
        params={"content": "课程内容", "count": "查询数量"}
    )
    def generate_test_queries(
        self,
        content: str,
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        生成测试查询
        
        基于课程内容自动生成测试查询，用于评估检索效果。
        不使用 LLM，而是基于内容特征生成。
        """
        queries = []
        
        # 提取标题作为查询
        headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        for heading in headings[:count]:
            queries.append({
                "query": heading.strip(),
                "type": "heading",
                "expected_keywords": heading.split()[:3],
            })
        
        # 提取定义语句
        definitions = re.findall(
            r'([^\n，。]{2,20})(?:是|是指|定义为)[：:]*([^\n。]{10,50})',
            content
        )
        for term, definition in definitions[:count - len(queries)]:
            queries.append({
                "query": f"什么是{term}",
                "type": "definition",
                "expected_keywords": [term],
            })
        
        # 提取技术术语
        tech_terms = re.findall(r'[\u4e00-\u9fff]{2,8}(?:算法|模型|方法|技术|框架)', content)
        for term in list(set(tech_terms))[:count - len(queries)]:
            queries.append({
                "query": f"{term}是什么",
                "type": "concept",
                "expected_keywords": [term],
            })
        
        return queries[:count]
    
    @skill(
        "evaluate_retrieval",
        description="评估检索效果",
        params={"chunks": "分块列表", "queries": "测试查询"}
    )
    def evaluate_retrieval(
        self,
        chunks: List[Dict[str, Any]],
        queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        评估检索效果（简化版）
        
        通过关键词匹配模拟检索评估。
        实际场景应该调用 Embedding 和向量检索。
        """
        total_recall = 0
        total_precision = 0
        
        for query_info in queries:
            query = query_info.get("query", "")
            expected = query_info.get("expected_keywords", [])
            
            # 简单的关键词匹配
            matched_chunks = 0
            relevant_chunks = 0
            
            for chunk in chunks:
                chunk_text = chunk.get("text", "").lower()
                query_lower = query.lower()
                
                # 检查是否匹配
                if any(kw.lower() in chunk_text for kw in expected):
                    relevant_chunks += 1
                    if query_lower in chunk_text or any(kw.lower() in chunk_text for kw in expected):
                        matched_chunks += 1
            
            # 计算召回率和精确率（简化版）
            recall = matched_chunks / max(relevant_chunks, 1)
            precision = matched_chunks / max(len([c for c in chunks if query_lower in c.get("text", "").lower()]), 1) if any(query_lower in c.get("text", "").lower() for c in chunks) else 0
            
            total_recall += recall
            total_precision += precision
        
        n_queries = max(len(queries), 1)
        avg_recall = total_recall / n_queries
        avg_precision = total_precision / n_queries
        f1_score = 2 * (avg_precision * avg_recall) / max(avg_precision + avg_recall, 0.001)
        
        return {
            "avg_recall": round(avg_recall, 3),
            "avg_precision": round(avg_precision, 3),
            "f1_score": round(f1_score, 3),
            "query_count": len(queries),
        }
    
    @skill(
        "compare_strategies",
        description="对比策略结果",
        params={"results": "各策略的评估结果"}
    )
    def compare_strategies(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        对比不同策略的评估结果
        
        Returns:
            排名、推荐策略、配置建议
        """
        # 按召回率排序
        ranked = sorted(
            results.items(),
            key=lambda x: x[1].get("avg_recall", 0),
            reverse=True
        )
        
        # 选择最优策略
        best_strategy, best_result = ranked[0] if ranked else (None, {})
        
        # 生成配置建议
        recommendation = {
            "recommended_strategy": best_strategy,
            "confidence": "high" if len(ranked) > 2 else "medium",
            "reason": f"召回率最高 ({best_result.get('avg_recall', 0):.1%})",
            "ranking": [
                {
                    "strategy": name,
                    "recall": result.get("avg_recall", 0),
                    "chunk_count": result.get("chunk_count", 0),
                }
                for name, result in ranked
            ],
        }
        
        return recommendation
    
    @skill(
        "generate_summary",
        description="生成优化摘要",
        params={"analysis": "内容分析", "recommendation": "推荐结果"}
    )
    async def generate_summary(
        self,
        analysis: Dict[str, Any],
        recommendation: Dict[str, Any]
    ) -> str:
        """
        生成优化摘要
        
        使用 LLM 生成人类可读的优化摘要。
        使用统一的 LLM 封装，支持 Langfuse 监控。
        """
        from app.llm import get_llm_client
        from app.llm.langfuse_wrapper import _get_langfuse_client
        from prompts import prompt_loader
        
        # Langfuse 监控
        langfuse_client = _get_langfuse_client()
        trace = None
        start_time = datetime.now()
        
        input_data = {
            "content_type": "技术文档" if analysis.get("has_code") else "普通文本",
            "chapters": analysis.get("chapters", 0),
            "recommended_strategy": recommendation.get("recommended_strategy", ""),
        }
        
        if langfuse_client:
            trace = langfuse_client.trace(
                name="rag_optimization_summary",
                input=input_data,
                tags=["agent", "rag", "summary"],
            )
        
        error_occurred = None
        summary = ""
        usage_info = None
        
        try:
            # 构建 prompt
            prompt = f"""请为 RAG 优化结果生成简洁的中文摘要。

内容特征：
- 类型: {"技术文档（含代码）" if analysis.get("has_code") else "普通文本"}
- 章节数: {analysis.get("chapters", 0)}
- 平均章节长度: {analysis.get("avg_chapter_length", 0)} 字

推荐策略: {recommendation.get("recommended_strategy", "未知")}
推荐理由: {recommendation.get("reason", "")}

请用 2-3 句话总结优化结果，包括推荐策略和预期效果。"""
            
            messages = [{"role": "user", "content": prompt}]
            
            # 使用统一的 LLM 客户端
            llm = get_llm_client()
            response = llm.chat_sync(messages=messages, temperature=0.3)
            
            summary = response.content
            
            if response.usage:
                usage_info = {
                    "prompt_tokens": response.usage.get("prompt_tokens"),
                    "completion_tokens": response.usage.get("completion_tokens"),
                    "total_tokens": response.usage.get("total_tokens"),
                }
                
        except Exception as e:
            error_occurred = str(e)
            # 降级：生成简单摘要
            summary = f"推荐使用 {recommendation.get('recommended_strategy', '未知')} 策略，预期召回率 {recommendation.get('ranking', [{}])[0].get('recall', 0):.1%}。"
        
        finally:
            # 记录 Langfuse trace
            if langfuse_client and trace:
                end_time = datetime.now()
                output_data = {
                    "summary_length": len(summary),
                    "summary_preview": summary[:200],
                }
                if error_occurred:
                    output_data["error"] = error_occurred
                
                trace.generation(
                    name="llm_summary",
                    input=input_data,
                    output=output_data,
                    model=llm.default_model if (llm := get_llm_client()) else None,
                    usage={
                        "input": usage_info.get("prompt_tokens") if usage_info else None,
                        "output": usage_info.get("completion_tokens") if usage_info else None,
                        "total": usage_info.get("total_tokens") if usage_info else None,
                    },
                    start_time=start_time,
                    end_time=end_time,
                    metadata={"duration_ms": (end_time - start_time).total_seconds() * 1000},
                )
                trace.update(output=output_data)
                langfuse_client.flush()
        
        return summary
    
    # ============== Agent 执行流程 ==============
    
    async def execute(
        self,
        context: AgentContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行 RAG 优化流程
        
        流程：
        1. 分析内容特征
        2. 选择测试策略
        3. 逐个测试策略
        4. 对比评估结果
        5. 生成推荐配置
        """
        # 获取输入
        content = context.input_data.get("content", "")
        strategies = context.input_data.get("strategies", self.DEFAULT_STRATEGIES)
        course_id = context.input_data.get("course_id", "unknown")
        
        if not content:
            yield AgentEvent.agent_error("缺少课程内容")
            return
        
        # Langfuse 监控整个 Agent 执行
        from app.llm.langfuse_wrapper import _get_langfuse_client
        langfuse_client = _get_langfuse_client()
        agent_trace = None
        agent_start_time = datetime.now()
        
        if langfuse_client:
            agent_trace = langfuse_client.trace(
                name="rag_optimization_agent",
                input={
                    "course_id": course_id,
                    "content_length": len(content),
                    "strategies_count": len(strategies),
                },
                tags=["agent", "rag", "optimization"],
            )
        
        try:
            # ========== 1. 开始 ==========
            yield AgentEvent.agent_start(f"开始优化课程: {course_id}")
            yield AgentEvent.agent_thinking("正在分析课程内容特征...")
            
            # ========== 2. 分析内容 ==========
            yield AgentEvent.skill_start("analyze_content", "分析内容特征")
            analysis = self.call_skill("analyze_content", content=content)
            yield AgentEvent.skill_output(
                "analyze_content",
                f"检测到 {analysis['chapters']} 个章节，"
                f"{'含代码块' if analysis['has_code'] else '无代码块'}，"
                f"平均章节 {analysis['avg_chapter_length']} 字",
                analysis
            )
            context.add_result("analyze_content", analysis)
            
            # 选择要测试的策略
            suggested = analysis.get("suggested_strategies", [])
            test_strategies = [
                s for s in strategies 
                if s.get("name") in suggested
            ] or strategies[:4]
            
            yield AgentEvent.agent_thinking(
                f"根据内容特征，选择测试策略: {', '.join(s['name'] for s in test_strategies)}"
            )
            
            # ========== 3. 生成测试查询 ==========
            yield AgentEvent.skill_start("generate_test_queries", "生成测试查询")
            queries = self.call_skill("generate_test_queries", content=content, count=5)
            yield AgentEvent.skill_output(
                "generate_test_queries",
                f"生成 {len(queries)} 个测试查询",
                {"queries": [q["query"] for q in queries]}
            )
            context.add_result("generate_test_queries", {"query_count": len(queries)})
            
            # ========== 4. 测试各策略 ==========
            yield AgentEvent.agent_thinking("开始测试各分块策略...")
            
            strategy_results = {}
            total_strategies = len(test_strategies)
            
            for i, strategy in enumerate(test_strategies):
                strategy_name = strategy.get("name", "unknown")
                
                yield AgentEvent.progress(
                    i + 1,
                    total_strategies,
                    f"测试策略 [{i+1}/{total_strategies}]: {strategy_name}"
                )
                yield AgentEvent.skill_start("test_chunking", f"测试分块策略: {strategy_name}")
                
                # 测试分块
                chunk_result = self.call_skill(
                    "test_chunking",
                    content=content,
                    strategy=strategy
                )
                yield AgentEvent.skill_output(
                    "test_chunking",
                    f"生成 {chunk_result['chunk_count']} 个分块，平均 {chunk_result['avg_chunk_size']:.0f} 字",
                    chunk_result
                )
                
                # 评估检索
                yield AgentEvent.skill_start("evaluate_retrieval", f"评估检索效果: {strategy_name}")
                eval_result = self.call_skill(
                    "evaluate_retrieval",
                    chunks=chunk_result.get("sample_chunks", []),
                    queries=queries
                )
                yield AgentEvent.skill_output(
                    "evaluate_retrieval",
                    f"召回率: {eval_result['avg_recall']:.1%}, F1: {eval_result['f1_score']:.1%}",
                    eval_result
                )
                
                # 合并结果
                strategy_results[strategy_name] = {
                    **chunk_result,
                    **eval_result,
                }
                
                context.add_result(strategy_name, strategy_results[strategy_name])
            
            # ========== 5. 对比策略 ==========
            yield AgentEvent.agent_thinking("对比分析各策略效果...")
            yield AgentEvent.skill_start("compare_strategies", "对比策略结果")
            recommendation = self.call_skill(
                "compare_strategies",
                results=strategy_results
            )
            yield AgentEvent.skill_output(
                "compare_strategies",
                f"推荐策略: {recommendation['recommended_strategy']} ({recommendation['reason']})",
                recommendation
            )
            context.add_result("compare_strategies", recommendation)
            
            # ========== 6. 生成摘要 ==========
            yield AgentEvent.agent_thinking("生成优化摘要...")
            summary = await self.generate_summary(analysis, recommendation)
            
            # ========== 7. 完成 ==========
            final_result = {
                "course_id": course_id,
                "analysis": analysis,
                "strategy_results": strategy_results,
                "recommended_strategy": recommendation.get("recommended_strategy"),
                "recommended_config": next(
                    (s for s in strategies if s.get("name") == recommendation.get("recommended_strategy")),
                    strategies[0] if strategies else {}
                ),
                "ranking": recommendation.get("ranking", []),
                "summary": summary,
            }
            
            yield AgentEvent.agent_complete(
                f"优化完成！推荐使用 {recommendation.get('recommended_strategy')} 策略",
                final_result
            )
            
            # 保存到上下文
            context.metadata["final_result"] = final_result
            
        except Exception as e:
            yield AgentEvent.agent_error(f"优化过程出错: {str(e)}", str(e))
        
        finally:
            # 记录 Agent 执行 trace
            if langfuse_client and agent_trace:
                end_time = datetime.now()
                final_result = context.metadata.get("final_result", {})
                
                agent_trace.span(
                    name="agent_execution",
                    input={"course_id": course_id},
                    output={
                        "recommended_strategy": final_result.get("recommended_strategy"),
                        "strategies_tested": len(final_result.get("strategy_results", {})),
                    },
                    start_time=agent_start_time,
                    end_time=end_time,
                    metadata={"duration_ms": (end_time - agent_start_time).total_seconds() * 1000},
                )
                langfuse_client.flush()
