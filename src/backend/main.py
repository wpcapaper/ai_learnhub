"""
FastAPI应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import users, review, quiz, exam, courses, question_sets, mistakes, learning

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
