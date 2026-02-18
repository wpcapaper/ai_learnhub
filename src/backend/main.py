"""
FastAPI应用入口
"""
from dotenv import load_dotenv
import os

# 加载环境变量 (必须在导入其他模块之前)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
from app.api import users, review, quiz, exam, courses, question_sets, mistakes, learning
=======
from app.api import users, review, quiz, exam, courses, question_sets, mistakes, rag
from app.models import init_db
>>>>>>> b3a7e721dcf014a17fa3deeef3db41995a8408f6

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

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库表"""
    init_db()


# 包含所有路由
app.include_router(users.router, prefix="/api", tags=["用户管理"])
app.include_router(review.router, prefix="/api", tags=["复习调度"])
app.include_router(quiz.router, prefix="/api", tags=["批次刷题"])
app.include_router(exam.router, prefix="/api", tags=["考试模式"])
app.include_router(courses.router, prefix="/api", tags=["课程管理"])
app.include_router(question_sets.router, prefix="/api", tags=["题集管理"])
app.include_router(mistakes.router, prefix="/api", tags=["错题管理"])
<<<<<<< HEAD
app.include_router(learning.router, prefix="/api", tags=["学习课程"])

=======
app.include_router(rag.router, tags=["RAG"])
>>>>>>> b3a7e721dcf014a17fa3deeef3db41995a8408f6

@app.get("/")
async def root():
    """根路径"""
    return {"message": "AILearn Hub API", "docs": "/docs"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
