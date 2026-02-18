from typing import List, Optional
import httpx

from .retriever import RetrievalResult


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
        if not results:
            return []
        
        # 构建请求
        documents = [{"id": r.chunk_id, "text": r.text} for r in results]
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.endpoint,
                    headers=headers,
                    json={"query": query, "documents": documents}
                )
                response.raise_for_status()
                data = response.json()
                
                # 解析重排序结果
                reranked_ids = [item["id"] for item in data.get("results", [])]
                scores_map = {item["id"]: item.get("score", 0.0) for item in data.get("results", [])}
                
                # 按重排序顺序重新排列结果
                id_to_result = {r.chunk_id: r for r in results}
                reranked = []
                for chunk_id in reranked_ids:
                    if chunk_id in id_to_result:
                        result = id_to_result[chunk_id]
                        result.score = scores_map.get(chunk_id, result.score)
                        reranked.append(result)
                
                if top_k is not None:
                    return reranked[:top_k]
                return reranked
                
        except httpx.HTTPStatusError as e:
            # 重排序失败时返回原始结果
            return results[:top_k] if top_k else results
        except Exception:
            return results[:top_k] if top_k else results
