"""
FastAPI应用入口
"""
from dotenv import load_dotenv
import os
import logging

# 加载环境变量 (必须在导入其他模块之前)
load_dotenv()

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import users, review, quiz, exam, courses, question_sets, mistakes, learning
from pathlib import Path


def _check_rag_configured() -> bool:
    """检查RAG是否已配置（有必要的API Key或服务地址）"""
    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "openai")
    
    if provider == "openai":
        return bool(os.getenv("RAG_OPENAI_API_KEY"))
    elif provider == "local":
        return bool(os.getenv("RAG_EMBEDDING_SERVICE_URL"))
    elif provider == "custom":
        return bool(os.getenv("RAG_EMBEDDING_ENDPOINT"))
    
    return bool(os.getenv("RAG_OPENAI_API_KEY"))


def _check_admin_configured() -> bool:
    """检查Admin模块是否可用"""
    return True


RAG_AVAILABLE = False
rag = None
try:
    from app.api import rag as rag_module
    if _check_rag_configured():
        rag = rag_module
        RAG_AVAILABLE = True
    else:
        logger.info("RAG 模块未配置，相关接口不可用。请设置 OPENAI_API_KEY 或其他Embedding配置")
except ImportError as e:
    logger.info(f"RAG 模块未安装，相关接口不可用: {e}")

ADMIN_AVAILABLE = False
admin = None
try:
    from app.api import admin as admin_module
    if _check_admin_configured():
        admin = admin_module
        ADMIN_AVAILABLE = True
except ImportError as e:
    logger.info(f"Admin 模块未安装，相关接口不可用: {e}")

app = FastAPI(
    title="AILearn Hub API",
    description="AI Learning System - Quiz and Exam Management",
    version="0.1.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含所有路由
app.include_router(users.router, prefix="/api", tags=["用户管理"])
app.include_router(review.router, prefix="/api", tags=["复习调度"])
app.include_router(quiz.router, prefix="/api", tags=["批次刷题"])
app.include_router(exam.router, prefix="/api", tags=["考试模式"])
app.include_router(courses.router, prefix="/api", tags=["课程管理"])
app.include_router(question_sets.router, prefix="/api", tags=["题集管理"])
app.include_router(mistakes.router, prefix="/api", tags=["错题管理"])
app.include_router(learning.router, prefix="/api", tags=["学习课程"])

# RAG 路由（弱依赖）
if RAG_AVAILABLE and rag:
    app.include_router(rag.router, prefix="/api", tags=["RAG"])

# Admin 路由（弱依赖）
if ADMIN_AVAILABLE and admin:
    app.include_router(admin.router, prefix="/api", tags=["Admin"])

# 挂载 courses 目录为静态文件服务，用于课程图片等资源访问
# Docker 环境中 courses 目录挂载在 /app/courses
courses_path = Path("/app/courses")
if not courses_path.exists():
    # 本地开发环境
    courses_path = Path(__file__).parent.parent.parent.parent / "courses"
if courses_path.exists():
    app.mount("/courses", StaticFiles(directory=str(courses_path)), name="courses")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "AILearn Hub API", "docs": "/docs"}


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "rag_available": RAG_AVAILABLE,
        "admin_available": ADMIN_AVAILABLE,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
