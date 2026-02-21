"""
异步任务模块

基于 Redis Queue (RQ) 实现的异步任务处理框架。
支持任务型 Agent（词云、知识图谱、Quiz 生成等）的后台执行。
"""

from .queue import (
    get_queue, 
    get_worker, 
    enqueue_task, 
    get_job_status, 
    cancel_job,
    cleanup_stale_jobs,
    acquire_course_lock,
    release_course_lock
)
from .base import AsyncTask, TaskStatus
from .jobs import (
    generate_wordcloud,
    generate_knowledge_graph,
    generate_quiz,
    index_chapter,
    index_course,
)

__all__ = [
    # 队列管理
    "get_queue",
    "get_worker",
    "enqueue_task",
    "get_job_status",
    "cancel_job",
    "cleanup_stale_jobs",
    "acquire_course_lock",
    "release_course_lock",
    # 任务基类
    "AsyncTask",
    "TaskStatus",
    # 任务函数
    "generate_wordcloud",
    "generate_knowledge_graph",
    "generate_quiz",
    "index_chapter",
    "index_course",
]
