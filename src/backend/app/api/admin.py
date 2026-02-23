"""
管理端 API 路由

提供课程管理、质量评估、RAG优化等管理功能

安全说明：
- 此路由已通过 AdminIPWhitelistMiddleware 进行 IP 白名单认证
- 所有路径参数已进行路径穿越验证

所有课程数据存储在 markdown_courses/ 目录，不依赖 courses/ 目录
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

# 课程转换管道
from app.course_pipeline import (
    CoursePipeline,
    ConversionResult,
    QualityReport,
)
from app.course_pipeline.pipeline import RAGChunkOptimizer
from app.course_pipeline.evaluators import load_quality_report
from app.course_pipeline.models import RawCourse, SourceFile

# Agent 框架
from app.agent import RAGOptimizerAgent, AgentEvent

# 数据库
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import Course, Chapter, Base

# 安全模块
from app.core.admin_security import validate_course_id

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== 请求/响应模型 ====================

class CourseInfo(BaseModel):
    course_info: str
    id: str
    code: str
    title: str
    description: str
    chapters: List[Dict[str, Any]]
    quality_score: Optional[int] = None
    created_at: Optional[str] = None


class ConvertResponse(BaseModel):
    convert_response: str
    message: str
    results: List[Dict[str, Any]]


class OptimizationRequest(BaseModel):
    optimization_request: str
    course_id: str
    strategies: Optional[List[Dict[str, Any]]] = None


class TaskResponse(BaseModel):
    task_response: str
    task_id: str
    status: str


class RawCourseInfo(BaseModel):
    raw_course_info: str
    id: str
    name: str
    path: str
    file_count: int
    has_content: bool


class DatabaseCourseInfo(BaseModel):
    database_course_info: str
    id: str
    code: str
    title: str
    description: Optional[str]
    course_type: str
    is_active: bool
    chapter_count: int
    created_at: Optional[str]


class DatabaseChapterInfo(BaseModel):
    database_chapter_info: str
    id: str
    course_id: str
    title: str
    sort_order: int


class ImportResult(BaseModel):
    import_result: str
    success: bool
    message: str
    imported_courses: int = 0
    imported_chapters: int = 0
    errors: List[str] = []


# ==================== 辅助函数 ====================

def get_raw_courses_dir() -> Path:
    docker_path = Path("/app/raw_courses")
    if docker_path.exists():
        return docker_path
    return Path(os.path.dirname(__file__)).parent.parent.parent.parent / "raw_courses"


def get_markdown_courses_dir() -> Path:
    docker_path = Path("/app/markdown_courses")
    if docker_path.exists():
        return docker_path
    return Path(os.path.dirname(__file__)).parent.parent.parent.parent / "markdown_courses"


def load_course_json(course_dir: Path) -> Optional[Dict[str, Any]]:
    course_json = course_dir / "course.json"
    if course_json.exists():
        with open(course_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_quality_report_from_course(course_dir: Path) -> Optional[QualityReport]:
    report_path = course_dir / "quality_report.json"
    return load_quality_report(report_path)


# ==================== 课程转换 API ====================

@router.post("/courses/convert/{course_name}", response_model=ConvertResponse)
async def convert_single_course(course_name: str):
    course_name = validate_course_id(course_name)
    raw_dir = get_raw_courses_dir()
    markdown_dir = get_markdown_courses_dir()
    
    source_dir = raw_dir / course_name
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail=f"原始课程不存在: {course_name}")
    
    source_files = []
    for ext in ['*.md', '*.ipynb']:
        for file_path in source_dir.rglob(ext):
            if '.ipynb_checkpoints' in str(file_path) or file_path.name.startswith('.'):
                continue
            source_files.append(SourceFile.from_path(str(file_path), str(source_dir)))
    
    if not source_files:
        raise HTTPException(status_code=400, detail=f"课程目录中没有可转换的文件: {course_name}")
    
    pipeline = CoursePipeline(
        raw_courses_dir=str(raw_dir),
        markdown_courses_dir=str(markdown_dir)
    )
    
    result = pipeline.convert_course(RawCourse(
        course_id=course_name,
        name=course_name,
        source_dir=str(source_dir),
        source_files=source_files
    ))
    
    result_data = {
        "success": result.success,
        "course_id": result.course.course_id if result.course else course_name,
        "code": result.course.code if result.course else None,
        "error": result.error_message if not result.success else None,
        "chapters": len(result.course.chapters) if result.course else 0,
        "quality_score": result.course.quality_report.overall_score if result.course and result.course.quality_report else None,
    }
    
    return ConvertResponse(
        message="转换成功" if result.success else f"转换失败: {result.error_message}",
        results=[result_data]
    )


@router.post("/courses/reorder/{code}", response_model=ConvertResponse)
async def reorder_course_chapters(code: str):
    """
    对已转换课程进行章节重排
    
    TODO: 实现章节重排逻辑
    1. 读取现有 markdown_courses/{code}/course.json
    2. 使用 ChapterSorter 重新排序
    3. 检测现有版本，生成新版本号 N
    4. 创建新目录 {code}_v{N}
    5. 复制内容，更新 course.json（添加 origin, version 字段）
    """
    code = validate_course_id(code)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / code
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail=f"课程不存在: {code}")
    
    pipeline = CoursePipeline(
        raw_courses_dir=str(get_raw_courses_dir()),
        markdown_courses_dir=str(markdown_dir)
    )
    
    try:
        result = pipeline.reorder_course(code)
        return ConvertResponse(
            message="章节重排成功",
            results=[{"success": True, "code": code}]
        )
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="章节重排功能待实现")


# ==================== 质量评估 API ====================

@router.get("/quality/{course_id}")
async def get_quality_report(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
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
    course_id = validate_course_id(request.course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
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
    
    optimizer = RAGChunkOptimizer()
    
    test_queries = [
        {"query": course_json.get("title", ""), "expected_keywords": [course_json.get("title", "")]},
    ]
    
    description = course_json.get("description", "")
    if description:
        import re
        keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', description)
        if keywords:
            test_queries.append({
                "query": description[:50],
                "expected_keywords": keywords[:5]
            })
    
    report = optimizer.test_chunk_strategies(
        content=full_content,
        test_queries=test_queries,
        strategies=request.strategies
    )
    
    report_path = course_dir / "rag_optimization_report.json"
    optimizer.save_optimization_report(report, report_path)
    
    return report


@router.get("/rag/optimize/{course_id}")
async def get_optimization_report(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    report_path = markdown_dir / course_id / "rag_optimization_report.json"
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="优化报告不存在，请先运行优化")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== 配置管理 API ====================

@router.get("/rag/config")
async def get_rag_config():
    config_path = Path(os.path.dirname(__file__)).parent / "config" / "rag_config.yaml"
    
    if not config_path.exists():
        return {"message": "配置文件不存在，使用默认配置"}
    
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


@router.put("/rag/config")
async def update_rag_config(config: Dict[str, Any]):
    config_path = Path(os.path.dirname(__file__)).parent / "config" / "rag_config.yaml"
    
    import yaml
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    return {"message": "配置已更新"}


# ==================== Agent SSE 流式 API ====================

@router.post("/rag/optimize/stream")
async def run_optimization_stream(request: OptimizationRequest):
    course_id = validate_course_id(request.course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
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
    agent = RAGOptimizerAgent()
    return {"skills": agent.skills}


# ==================== 原始课程 API ====================

@router.get("/raw-courses", response_model=List[RawCourseInfo])
async def list_raw_courses():
    raw_courses = []
    raw_dir = get_raw_courses_dir()
    
    if not raw_dir.exists():
        return raw_courses
    
    for course_dir in raw_dir.iterdir():
        if not course_dir.is_dir():
            continue
        if course_dir.name.startswith('.'):
            continue
        
        file_count = 0
        md_count = 0
        
        for f in course_dir.rglob("*"):
            if f.is_file() and not f.name.startswith('.'):
                file_count += 1
                if f.suffix == '.md':
                    md_count += 1
        
        raw_courses.append(RawCourseInfo(
            id=course_dir.name,
            name=course_dir.name,
            path=str(course_dir.relative_to(raw_dir.parent)),
            file_count=file_count,
            has_content=md_count > 0
        ))
    
    return raw_courses


@router.get("/markdown-courses", response_model=List[CourseInfo])
async def list_markdown_courses():
    markdown_courses = []
    markdown_dir = get_markdown_courses_dir()
    
    if not markdown_dir.exists():
        return markdown_courses
    
    for course_dir in markdown_dir.iterdir():
        if not course_dir.is_dir():
            continue
        if course_dir.name.startswith('.'):
            continue
        
        course_json = load_course_json(course_dir)
        if not course_json:
            continue
        
        quality_report = load_quality_report_from_course(course_dir)
        quality_score = quality_report.overall_score if quality_report else None
        
        markdown_courses.append(CourseInfo(
            id=course_dir.name,
            code=course_json.get("code", course_dir.name),
            title=course_json.get("title", course_dir.name),
            description=course_json.get("description", ""),
            chapters=course_json.get("chapters", []),
            quality_score=quality_score,
            created_at=None
        ))
    
    markdown_courses.sort(key=lambda x: x.title)
    
    return markdown_courses


@router.get("/markdown-courses/{course_id}", response_model=CourseInfo)
async def get_markdown_course(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    course_json = load_course_json(course_dir)
    if not course_json:
        raise HTTPException(status_code=404, detail="course.json 不存在")
    
    quality_report = load_quality_report_from_course(course_dir)
    quality_score = quality_report.overall_score if quality_report else None
    
    return CourseInfo(
        id=course_id,
        code=course_json.get("code", course_id),
        title=course_json.get("title", course_id),
        description=course_json.get("description", ""),
        chapters=course_json.get("chapters", []),
        quality_score=quality_score,
        created_at=None
    )


@router.get("/markdown-courses/{course_id}/course.json")
async def get_course_json(course_id: str):
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    course_json = load_course_json(course_dir)
    if not course_json:
        raise HTTPException(status_code=404, detail="course.json 不存在")
    
    return course_json


# ==================== 数据库课程 API ====================

@router.get("/database/courses", response_model=List[DatabaseCourseInfo])
async def list_database_courses():
    db = SessionLocal()
    try:
        courses = db.query(Course).filter(Course.is_deleted == False).all()
        
        result = []
        for course in courses:
            chapter_count = db.query(Chapter).filter(Chapter.course_id == course.id).count()
            
            result.append(DatabaseCourseInfo(
                id=course.id,
                code=course.code,
                title=course.title,
                description=course.description,
                course_type=course.course_type,
                is_active=course.is_active,
                chapter_count=chapter_count,
                created_at=course.created_at.isoformat() if course.created_at else None
            ))
        
        return result
    finally:
        db.close()


@router.get("/database/courses/{course_id}/chapters", response_model=List[DatabaseChapterInfo])
async def list_database_chapters(course_id: str):
    db = SessionLocal()
    try:
        chapters = db.query(Chapter).filter(
            Chapter.course_id == course_id,
            Chapter.is_deleted == False
        ).order_by(Chapter.sort_order).all()
        
        return [
            DatabaseChapterInfo(
                id=chapter.id,
                course_id=chapter.course_id,
                title=chapter.title,
                sort_order=chapter.sort_order
            )
            for chapter in chapters
        ]
    finally:
        db.close()


@router.post("/markdown-courses/{course_id}/import", response_model=ImportResult)
async def import_markdown_course_to_database(course_id: str):
    """
    将已转换课程导入到数据库
    
    Args:
        course_id: markdown_courses 目录名（如 python_basics 或 python_basics_v1）
    
    导入时使用 UUID 作为数据库主键，用 code 查重
    """
    course_id = validate_course_id(course_id)
    db = SessionLocal()
    
    try:
        markdown_dir = get_markdown_courses_dir()
        course_dir = markdown_dir / course_id
        
        if not course_dir.exists():
            raise HTTPException(status_code=404, detail=f"课程目录不存在: {course_id}")
        
        course_json = load_course_json(course_dir)
        if not course_json:
            raise HTTPException(status_code=404, detail=f"课程配置文件不存在: {course_id}")
        
        course_code = course_json.get("code", course_id)
        
        existing = db.query(Course).filter(Course.code == course_code, Course.is_deleted == False).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"课程代码已存在: {course_code}")
        
        course = Course(
            id=str(uuid.uuid4()),
            code=course_code,
            title=course_json.get("title", course_id),
            description=course_json.get("description", ""),
            course_type=course_json.get("course_type", "learning"),
            cover_image=course_json.get("cover_image"),
            default_exam_config=None,
            is_active=True,
            sort_order=course_json.get("sort_order", 0),
            created_at=datetime.utcnow()
        )
        db.add(course)
        db.flush()
        
        imported_chapters = 0
        errors = []
        
        chapters = course_json.get("chapters", [])
        for chapter_info in chapters:
            chapter_file = course_dir / chapter_info.get("file", "")
            
            if not chapter_file.exists():
                errors.append(f"{chapter_info.get('file')}: 文件不存在")
                continue
            
            markdown_content = chapter_file.read_text(encoding='utf-8')
            
            chapter = Chapter(
                id=str(uuid.uuid4()),
                course_id=course.id,
                title=chapter_info.get("title", ""),
                content_markdown=markdown_content,
                sort_order=chapter_info.get("sort_order", 0)
            )
            
            db.add(chapter)
            imported_chapters += 1
        
        db.commit()
        
        return ImportResult(
            success=True,
            message=f"导入成功: {course.title}",
            imported_courses=1,
            imported_chapters=imported_chapters,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        db.close()


class CourseActivateRequest(BaseModel):
    course_activate_request: str
    is_active: bool


@router.put("/database/courses/{course_id}/activate")
async def activate_course(course_id: str, request: CourseActivateRequest):
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        course.is_active = request.is_active
        db.commit()
        
        status = "已启用" if request.is_active else "已停用"
        return {"message": f"课程{status}", "course_id": course_id, "is_active": request.is_active}
    finally:
        db.close()


@router.delete("/database/courses/{course_id}")
async def delete_course_from_database(course_id: str):
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        course.is_deleted = True
        db.commit()
        
        return {"message": "课程已删除", "course_id": course_id}
    finally:
        db.close()


# ==================== 词云管理 API ====================

from app.services.wordcloud_service import WordcloudService


class WordcloudResponse(BaseModel):
    wordcloud_response: str
    version: str = "1.0"
    generated_at: str = ""
    words: List[Dict[str, float]] = []
    source_stats: Dict = {}


class WordcloudStatusResponse(BaseModel):
    wordcloud_status_response: str
    has_wordcloud: bool
    generated_at: Optional[str] = None
    words_count: int = 0


class ChapterWordcloudStatus(BaseModel):
    chapter_wordcloud_status: str
    name: str
    path: str
    has_wordcloud: bool


class BatchGenerateResult(BaseModel):
    batch_generate_result: str
    success: bool
    message: str
    course_wordcloud: Optional[Dict] = None
    chapters_processed: int = 0
    chapters_total: int = 0
    errors: List[str] = []


def get_wordcloud_service() -> WordcloudService:
    return WordcloudService(courses_dir=str(get_markdown_courses_dir()))


@router.get("/courses/{course_id}/wordcloud")
async def get_course_wordcloud(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    wc_service = get_wordcloud_service()
    wordcloud_data = wc_service.get_course_wordcloud(course_dir)
    
    if not wordcloud_data:
        raise HTTPException(status_code=404, detail="词云未生成")
    
    return wordcloud_data


@router.post("/courses/{course_id}/wordcloud")
async def generate_course_wordcloud(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    wc_service = get_wordcloud_service()
    
    try:
        wordcloud_data = wc_service.generate_course_wordcloud(course_dir)
        return {
            "success": True,
            "message": "词云生成成功",
            "data": wordcloud_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"词云生成失败: {str(e)}")


@router.delete("/courses/{course_id}/wordcloud")
async def delete_course_wordcloud(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    wc_service = get_wordcloud_service()
    deleted = wc_service.delete_course_wordcloud(course_dir)
    
    if deleted:
        return {"success": True, "message": "词云已删除"}
    else:
        return {"success": False, "message": "词云不存在"}


@router.get("/courses/{course_id}/wordcloud/status", response_model=WordcloudStatusResponse)
async def get_course_wordcloud_status(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    wc_service = get_wordcloud_service()
    wordcloud_data = wc_service.get_course_wordcloud(course_dir)
    
    if wordcloud_data:
        return WordcloudStatusResponse(
            has_wordcloud=True,
            generated_at=wordcloud_data.get("generated_at"),
            words_count=len(wordcloud_data.get("words", []))
        )
    else:
        return WordcloudStatusResponse(
            has_wordcloud=False,
            generated_at=None,
            words_count=0
        )


@router.get("/courses/{course_id}/chapters/{chapter_name}/wordcloud")
async def get_chapter_wordcloud(course_id: str, chapter_name: str):
    course_id = validate_course_id(course_id)
    chapter_name = validate_course_id(chapter_name)
    
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    wc_service = get_wordcloud_service()
    wordcloud_data = wc_service.get_chapter_wordcloud(course_dir, chapter_name)
    
    if not wordcloud_data:
        raise HTTPException(status_code=404, detail="章节词云未生成")
    
    return wordcloud_data


@router.post("/courses/{course_id}/chapters/{chapter_name}/wordcloud")
async def generate_chapter_wordcloud(course_id: str, chapter_name: str):
    course_id = validate_course_id(course_id)
    chapter_name = validate_course_id(chapter_name)
    
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    chapter_file = None
    for md_file in course_dir.glob("**/*.md"):
        if md_file.stem == chapter_name:
            chapter_file = md_file
            break
    
    if not chapter_file:
        raise HTTPException(status_code=404, detail=f"章节文件不存在: {chapter_name}")
    
    wc_service = get_wordcloud_service()
    
    try:
        wordcloud_data = wc_service.generate_chapter_wordcloud(chapter_file)
        return {
            "success": True,
            "message": "章节词云生成成功",
            "data": wordcloud_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"词云生成失败: {str(e)}")


@router.get("/courses/{course_id}/chapters/wordcloud-status")
async def list_chapter_wordcloud_status(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    wc_service = get_wordcloud_service()
    chapters = wc_service.list_chapter_wordclouds(course_dir)
    
    return [ChapterWordcloudStatus(**ch) for ch in chapters]


@router.post("/courses/{course_id}/wordcloud/batch", response_model=BatchGenerateResult)
async def batch_generate_wordclouds(course_id: str):
    course_id = validate_course_id(course_id)
    markdown_dir = get_markdown_courses_dir()
    course_dir = markdown_dir / course_id
    
    if not course_dir.exists():
        raise HTTPException(status_code=404, detail="课程不存在")
    
    wc_service = get_wordcloud_service()
    
    try:
        result = wc_service.batch_generate_wordclouds(course_dir)
        
        return BatchGenerateResult(
            success=len(result["errors"]) == 0,
            message="批量生成完成" if result["course"] else "部分生成失败",
            course_wordcloud=result["course"],
            chapters_processed=len(result["chapters"]),
            chapters_total=len(result["chapters"]) + len([e for e in result["errors"] if "章节" in e]),
            errors=result["errors"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量生成失败: {str(e)}")
