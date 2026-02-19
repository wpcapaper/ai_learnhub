"""
管理端 API 路由

提供课程管理、质量评估、RAG优化等管理功能
注意：这些API应有独立的访问控制（如IP白名单）

所有RAG相关数据独立存储，不依赖业务数据库(app.db)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import uuid
from pathlib import Path

# 课程转换管道
from app.course_pipeline import (
    CoursePipeline,
    ConversionResult,
    QualityReport,
)
from app.course_pipeline.pipeline import RAGChunkOptimizer
from app.course_pipeline.evaluators import load_quality_report

# Agent 框架
from app.agent import RAGOptimizerAgent, AgentEvent

router = APIRouter(prefix="/admin", tags=["Admin"])

# ==================== 请求/响应模型 ====================

class CourseInfo(BaseModel):
    """课程信息"""
    id: str
    code: str
    title: str
    description: str
    chapters: List[Dict[str, Any]]
    quality_score: Optional[int] = None
    created_at: Optional[str] = None


class ConvertResponse(BaseModel):
    """转换响应"""
    message: str
    results: List[Dict[str, Any]]


class OptimizationRequest(BaseModel):
    """优化请求"""
    course_id: str
    strategies: Optional[List[Dict[str, Any]]] = None


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str


# ==================== 辅助函数 ====================

def get_courses_dir() -> Path:
    """获取课程目录路径"""
    # 相对于项目根目录
    return Path(os.path.dirname(__file__)).parent.parent.parent.parent.parent / "courses"


def get_raw_courses_dir() -> Path:
    """获取原始课程目录路径"""
    return Path(os.path.dirname(__file__)).parent.parent.parent.parent.parent / "raw_courses"


def load_course_json(course_dir: Path) -> Optional[Dict[str, Any]]:
    """加载课程的 course.json"""
    course_json = course_dir / "course.json"
    if course_json.exists():
        with open(course_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_quality_report_from_course(course_dir: Path) -> Optional[QualityReport]:
    """从课程目录加载质量报告"""
    report_path = course_dir / "quality_report.json"
    return load_quality_report(report_path)


# ==================== 课程管理 API ====================

@router.get("/courses", response_model=List[CourseInfo])
async def list_courses():
    """
    列出所有课程
    
    扫描 courses 目录，返回所有课程信息
    """
    courses = []
    courses_dir = get_courses_dir()
    
    if not courses_dir.exists():
        return courses
    
    for course_dir in courses_dir.iterdir():
        if not course_dir.is_dir():
            continue
        
        course_json = load_course_json(course_dir)
        if not course_json:
            continue
        
        # 加载质量报告获取评分
        quality_report = load_quality_report_from_course(course_dir)
        quality_score = quality_report.overall_score if quality_report else None
        
        courses.append(CourseInfo(
            id=course_dir.name,
            code=course_json.get("code", course_dir.name),
            title=course_json.get("title", course_dir.name),
            description=course_json.get("description", ""),
            chapters=course_json.get("chapters", []),
            quality_score=quality_score
        ))
    
    return courses


@router.get("/courses/{course_id}", response_model=CourseInfo)
async def get_course(course_id: str):
    """获取单个课程详情"""
    courses_dir = get_courses_dir()
    course_dir = courses_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    course_json = load_course_json(course_dir)
    if not course_json:
        raise HTTPException(status_code=404, detail="课程配置文件不存在")
    
    quality_report = load_quality_report_from_course(course_dir)
    quality_score = quality_report.overall_score if quality_report else None
    
    return CourseInfo(
        id=course_id,
        code=course_json.get("code", course_id),
        title=course_json.get("title", course_id),
        description=course_json.get("description", ""),
        chapters=course_json.get("chapters", []),
        quality_score=quality_score
    )


@router.post("/courses/convert", response_model=ConvertResponse)
async def convert_courses(background_tasks: BackgroundTasks):
    """
    触发课程转换
    
    将 raw_courses 目录下的原始课程转换为标准格式
    """
    raw_dir = str(get_raw_courses_dir())
    courses_dir = str(get_courses_dir())
    
    pipeline = CoursePipeline(
        raw_courses_dir=raw_dir,
        courses_dir=courses_dir
    )
    
    # 执行转换
    results = pipeline.convert_all()
    
    # 转换结果
    result_list = []
    for result in results:
        result_data = {
            "success": result.success,
            "course_id": result.course.course_id if result.course else None,
            "error": result.error_message if not result.success else None,
            "chapters": len(result.course.chapters) if result.course else 0,
            "quality_score": result.course.quality_report.overall_score if result.course and result.course.quality_report else None,
        }
        result_list.append(result_data)
    
    return ConvertResponse(
        message=f"转换完成，成功 {sum(1 for r in results if r.success)}/{len(results)}",
        results=result_list
    )


# ==================== 质量评估 API ====================

@router.get("/quality/{course_id}")
async def get_quality_report(course_id: str):
    """获取课程质量评估报告"""
    courses_dir = get_courses_dir()
    course_dir = courses_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    report = load_quality_report_from_course(course_dir)
    if not report:
        raise HTTPException(status_code=404, detail="质量报告不存在，请先运行课程转换")
    
    return {
        "report_id": report.report_id,
        "course_id": report.course_id,
        "overall_score": report.overall_score,
        "completeness_score": report.completeness_score,
        "consistency_score": report.consistency_score,
        "accuracy_score": report.accuracy_score,
        "total_issues": report.total_issues,
        "critical_issues": report.critical_issues,
        "high_issues": report.high_issues,
        "medium_issues": report.medium_issues,
        "low_issues": report.low_issues,
        "summary": report.summary,
        "recommendations": report.recommendations,
        "evaluated_at": report.evaluated_at.isoformat(),
        "issues": [
            {
                "issue_id": issue.issue_id,
                "issue_type": issue.issue_type.value,
                "severity": issue.severity.value,
                "file_name": issue.file_name,
                "title": issue.title,
                "description": issue.description,
                "suggestion": issue.suggestion,
                "status": issue.status,
            }
            for issue in report.issues
        ]
    }


# ==================== RAG 优化 API ====================

@router.post("/rag/optimize")
async def run_optimization(request: OptimizationRequest):
    """
    运行RAG分块策略优化
    
    在沙箱环境中测试不同分块策略，返回推荐配置
    """
    courses_dir = get_courses_dir()
    course_dir = courses_dir / request.course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    # 加载课程内容
    course_json = load_course_json(course_dir)
    if not course_json:
        raise HTTPException(status_code=404, detail="课程配置不存在")
    
    # 读取所有章节内容
    content_parts = []
    for chapter in course_json.get("chapters", []):
        chapter_file = course_dir / chapter.get("file", "")
        if chapter_file.exists():
            with open(chapter_file, 'r', encoding='utf-8') as f:
                content_parts.append(f.read())
    
    if not content_parts:
        raise HTTPException(status_code=400, detail="课程内容为空")
    
    full_content = "\n\n".join(content_parts)
    
    # 创建优化器并运行测试
    optimizer = RAGChunkOptimizer()
    
    # 准备测试查询（基于课程内容生成简单测试）
    test_queries = [
        {"query": course_json.get("title", ""), "expected_keywords": [course_json.get("title", "")]},
    ]
    
    # 从课程描述中提取关键词
    description = course_json.get("description", "")
    if description:
        # 简单提取关键词
        import re
        keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', description)
        if keywords:
            test_queries.append({
                "query": description[:50],
                "expected_keywords": keywords[:5]
            })
    
    # 运行优化测试
    report = optimizer.test_chunk_strategies(
        content=full_content,
        test_queries=test_queries,
        strategies=request.strategies
    )
    
    # 保存报告
    report_path = course_dir / "rag_optimization_report.json"
    optimizer.save_optimization_report(report, report_path)
    
    return report


@router.get("/rag/optimize/{course_id}")
async def get_optimization_report(course_id: str):
    """获取已保存的优化报告"""
    courses_dir = get_courses_dir()
    report_path = courses_dir / course_id / "rag_optimization_report.json"
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="优化报告不存在，请先运行优化")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== 配置管理 API ====================

@router.get("/rag/config")
async def get_rag_config():
    """
    获取RAG配置
    
    返回当前的RAG配置信息
    """
    config_path = Path(os.path.dirname(__file__)).parent / "config" / "rag_config.yaml"
    
    if not config_path.exists():
        return {"message": "配置文件不存在，使用默认配置"}
    
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


@router.put("/rag/config")
async def update_rag_config(config: Dict[str, Any]):
    """
    更新RAG配置
    
    注意：此操作会影响全局RAG行为
    """
    config_path = Path(os.path.dirname(__file__)).parent / "config" / "rag_config.yaml"
    
    import yaml
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    return {"message": "配置已更新"}


# ==================== Agent SSE 流式 API ====================

@router.post("/rag/optimize/stream")
async def run_optimization_stream(request: OptimizationRequest):
    """
    运行 RAG 优化（SSE 流式输出）
    
    使用 Agent 框架执行优化，实时输出执行过程。
    返回 SSE 格式的流式数据。
    """
    courses_dir = get_courses_dir()
    course_dir = courses_dir / request.course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    course_json = load_course_json(course_dir)
    if not course_json:
        raise HTTPException(status_code=404, detail="课程配置不存在")
    
    content_parts = []
    for chapter in course_json.get("chapters", []):
        chapter_file = course_dir / chapter.get("file", "")
        if chapter_file.exists():
            with open(chapter_file, 'r', encoding='utf-8') as f:
                content_parts.append(f.read())
    
    if not content_parts:
        raise HTTPException(status_code=400, detail="课程内容为空")
    
    full_content = "\n\n".join(content_parts)
    
    async def event_generator():
        agent = RAGOptimizerAgent()
        task_id = str(uuid.uuid4())[:8]
        
        async for event in agent.run(
            task_id=task_id,
            content=full_content,
            course_id=request.course_id,
            strategies=request.strategies,
        ):
            yield event.to_sse()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/agent/skills")
async def list_agent_skills():
    """列出 Agent 可用的 Skills"""
    agent = RAGOptimizerAgent()
    return {"skills": agent.skills}
