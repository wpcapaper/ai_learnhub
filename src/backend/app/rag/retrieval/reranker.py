from typing import List, Optional
import httpx
import logging

from .retriever import RetrievalResult

logger = logging.getLogger(__name__)


class Reranker:
    """远程重排序服务客户端，用于提升检索精确度"""
    
    def __init__(self, endpoint: str, timeout: int = 30, api_key: Optional[str] = None):
        """
        Args:
            endpoint: 重排序服务地址
            timeout: 请求超时时间（秒）
            api_key: 可选的 API 密钥
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.api_key = api_key
    
    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        对检索结果进行重排序
        
        Args:
            query: 用户查询文本
            results: 原始检索结果列表
            top_k: 返回 Top K 结果（None 表示返回全部）
        
        Returns:
            重排序后的结果列表
        """
        return self._rerank_with_tracing(query, results, top_k)
    
    def _rerank_with_tracing(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """带 Langfuse 追踪的重排序实现"""
        from app.llm.langfuse_wrapper import _get_langfuse_client
        from datetime import datetime as dt
        
        langfuse_client = _get_langfuse_client()
        trace = None
        start_time = dt.now()
        
        # 准备 trace 输入数据
        input_data = {
            "query": query[:200],
            "result_count": len(results),
        }
        
        if langfuse_client:
            trace = langfuse_client.trace(
                name="search_rerank",
                input=input_data,
                tags=["rag", "rerank"],
            )
        
        error_occurred = None
        reranked = results[:top_k] if top_k else results
        
        try:
            if not results:
                return []
            
            documents = [{"id": r.chunk_id, "text": r.text} for r in results]
            
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.endpoint,
                    headers=headers,
                    json={"query": query, "documents": documents}
                )
                response.raise_for_status()
                data = response.json()
                
                reranked_ids = [item["id"] for item in data.get("results", [])]
                scores_map = {item["id"]: item.get("score", 0.0) for item in data.get("results", [])}
                
                id_to_result = {r.chunk_id: r for r in results}
                reranked = []
                for chunk_id in reranked_ids:
                    if chunk_id in id_to_result:
                        result = id_to_result[chunk_id]
                        result.score = scores_map.get(chunk_id, result.score)
                        reranked.append(result)
                
                if top_k is not None:
                    reranked = reranked[:top_k]
                    
            return reranked
                
        except httpx.HTTPStatusError as e:
            error_occurred = f"HTTP {e.response.status_code}"
            return results[:top_k] if top_k else results
        except Exception as e:
            error_occurred = str(e)
            return results[:top_k] if top_k else results
        finally:
            # 记录 trace 到 Langfuse
            if langfuse_client and trace:
                end_time = dt.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                output_data = {
                    "reranked_count": len(reranked),
                }
                
                if error_occurred:
                    output_data["error"] = error_occurred
                
                trace.span(
                    name="rerank_call",
                    input=input_data,
                    output=output_data,
                    start_time=start_time,
                    end_time=end_time,
                    metadata={"duration_ms": duration_ms},
                )
                
                trace.update(output=output_data)
                langfuse_client.flush()
