from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.rag.service import RAGService
from app.rag.retrieval import RetrievalResult
from app.rag.evaluation import RecallTester, TestCase
from app.rag.embedding import EmbeddingModelFactory

router = APIRouter(prefix="/rag", tags=["RAG"])


def get_rag_service() -> RAGService:
    """获取 RAG 服务单例实例"""
    return RAGService.get_instance()


# ========== 请求/响应模型 ==========

class IndexContentRequest(BaseModel):
    """索引内容请求"""
    content: str
    course_code: str  # 课程唯一标识（如 python_basics），非数据库 UUID
    chapter_id: Optional[str] = None
    chapter_title: Optional[str] = None
    clear_existing: bool = False


class IndexContentResponse(BaseModel):
    """索引内容响应"""
    chunk_count: int
    message: str


class RetrieveRequest(BaseModel):
    """检索请求"""
    query: str
    course_code: str  # 课程唯一标识（如 python_basics），非数据库 UUID
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None
    score_threshold: float = 0.0
    use_expansion: Optional[bool] = None


class RetrievalResultResponse(BaseModel):
    """检索结果响应"""
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    score: float
    source: str


class RetrieveResponse(BaseModel):
    """检索响应"""
    query: str
    results: List[RetrievalResultResponse]
    total: int


class TestCaseRequest(BaseModel):
    """测试用例请求"""
    query: str
    relevant_chunk_ids: List[str]


class RunTestRequest(BaseModel):
    """运行测试请求"""
    test_cases: List[TestCaseRequest]
    course_code: str  # 课程唯一标识（如 python_basics）
    top_k: int = 5
    score_threshold: float = 0.0


# ========== API端点 ==========

@router.post("/index", response_model=IndexContentResponse)
async def index_content(
    request: IndexContentRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    索引课程内容
    
    将课程内容切割、编码并存储到向量数据库
    """
    try:
        chunk_count = await rag_service.index_course_content(
            content=request.content,
            course_id=request.course_code,
            chapter_id=request.chapter_id,
            chapter_title=request.chapter_title,
            clear_existing=request.clear_existing
        )
        
        return IndexContentResponse(
            chunk_count=chunk_count,
            message=f"成功索引 {chunk_count} 个文档片段"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引失败: {str(e)}")


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(
    request: RetrieveRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    检索相关内容
    
    根据查询文本从课程内容中检索相关片段
    """
    try:
        results = await rag_service.retrieve(
            query=request.query,
            course_id=request.course_code,
            top_k=request.top_k,
            filters=request.filters,
            score_threshold=request.score_threshold,
            use_expansion=request.use_expansion
        )
        
        # 转换为响应模型
        result_responses = [
            RetrievalResultResponse(
                chunk_id=r.chunk_id,
                text=r.text,
                metadata=r.metadata,
                score=r.score,
                source=r.source
            )
            for r in results
        ]
        
        return RetrieveResponse(
            query=request.query,
            results=result_responses,
            total=len(result_responses)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/models")
async def list_embedding_models():
    """列出所有可用的Embedding模型"""
    models = EmbeddingModelFactory.list_models()
    return {"models": models}


@router.get("/collection/{course_code}/size")
async def get_collection_size(
    course_code: str,
    rag_service: RAGService = Depends(get_rag_service)
):
    """获取课程索引的大小"""
    try:
        size = rag_service.get_collection_size(course_code)
        return {"course_code": course_code, "chunk_count": size}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.delete("/collection/{course_code}")
async def delete_collection(
    course_code: str,
    rag_service: RAGService = Depends(get_rag_service)
):
    """删除课程索引"""
    try:
        rag_service.delete_course_index(course_code)
        return {"message": f"成功删除课程 {course_code} 的索引"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/test/recall")
async def test_recall(
    request: RunTestRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    运行召回测试
    
    评估RAG系统的召回率、精确率等指标
    """
    try:
        # 构建测试用例
        test_cases = [
            TestCase(
                query=tc.query,
                relevant_chunk_ids=tc.relevant_chunk_ids
            )
            for tc in request.test_cases
        ]
        
        # 创建测试器
        retriever = rag_service.get_retriever(request.course_code)
        tester = RecallTester(retriever)
        
        # 运行测试
        report = await tester.run_test(
            test_cases=test_cases,
            course_id=request.course_code,
            top_k=request.top_k,
            score_threshold=request.score_threshold
        )
        
        # 返回结果
        return {
            "total_queries": report.total_queries,
            "avg_recall_at_k": report.avg_recall_at_k,
            "avg_precision_at_k": report.avg_precision_at_k,
            "avg_mrr": report.avg_mrr,
            "results": [
                {
                    "query": r.query,
                    "retrieved_chunk_ids": r.retrieved_chunk_ids,
                    "relevant_chunk_ids": r.relevant_chunk_ids,
                    "recall_at_k": r.recall_at_k,
                    "precision_at_k": r.precision_at_k,
                    "mrr": r.mrr
                }
                for r in report.results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")
