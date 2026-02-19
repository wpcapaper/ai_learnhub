"""
Redis Queue (RQ) 队列管理

提供任务队列的初始化、任务入队和 Worker 管理。
"""

import os
import logging
from typing import Optional, Callable, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)

# 全局队列实例
_queue = None


def get_redis_url() -> str:
    """获取 Redis 连接 URL"""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_queue(name: str = "default"):
    """
    获取或创建 RQ 队列
    
    Args:
        name: 队列名称，默认为 "default"
    
    Returns:
        RQ Queue 实例
    """
    global _queue
    
    if _queue is not None:
        return _queue
    
    try:
        from rq import Queue
        from redis import Redis
        
        redis_conn = Redis.from_url(get_redis_url())
        _queue = Queue(name, connection=redis_conn)
        logger.info(f"RQ 队列已初始化: {name}")
        return _queue
    
    except ImportError:
        logger.warning("rq 或 redis 未安装，异步任务功能不可用")
        return None


def get_worker(queues: Optional[list] = None):
    """
    创建 RQ Worker
    
    Args:
        queues: 要监听的队列列表，默认为 ["default"]
    
    Returns:
        RQ Worker 实例
    """
    try:
        from rq import Worker
        from redis import Redis
        
        redis_conn = Redis.from_url(get_redis_url())
        queue_names = queues or ["default"]
        
        qs = [get_queue(name) for name in queue_names]
        worker = Worker(qs, connection=redis_conn)
        
        return worker
    
    except ImportError:
        logger.warning("rq 或 redis 未安装")
        return None


def enqueue_task(
    func: Callable,
    *args,
    **kwargs
) -> Optional[str]:
    """
    将任务加入队列
    
    Args:
        func: 要执行的任务函数
        *args: 任务函数的位置参数
        **kwargs: 任务函数的关键字参数
            - queue_name: 指定队列名称（可选）
            - timeout: 任务超时时间（可选）
            - 其他参数会传递给任务函数
    
    Returns:
        任务 ID，如果队列为 None 则返回 None
    """
    queue_name = kwargs.pop("queue_name", "default")
    timeout = kwargs.pop("timeout", 300)  # 默认 5 分钟超时
    
    queue = get_queue(queue_name)
    
    if queue is None:
        logger.warning(f"队列 {queue_name} 不可用，同步执行任务")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            raise
    
    try:
        job = queue.enqueue(
            func,
            *args,
            **kwargs,
            job_timeout=timeout,
            result_ttl=3600,  # 结果保留 1 小时
        )
        logger.info(f"任务已入队: {job.id}")
        return job.id
    
    except Exception as e:
        logger.error(f"任务入队失败: {e}")
        raise


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    获取任务状态
    
    Args:
        job_id: 任务 ID
    
    Returns:
        任务状态字典，包含 status, result, error 等字段
    """
    try:
        from rq.job import Job
        from redis import Redis
        
        redis_conn = Redis.from_url(get_redis_url())
        job = Job.fetch(job_id, connection=redis_conn)
        
        return {
            "id": job.id,
            "status": job.get_status(),
            "result": job.result,
            "error": job.exc_info,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }
    
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return None


def cancel_job(job_id: str) -> bool:
    """
    取消任务
    
    Args:
        job_id: 任务 ID
    
    Returns:
        是否取消成功
    """
    try:
        from rq.job import Job
        from redis import Redis
        
        redis_conn = Redis.from_url(get_redis_url())
        job = Job.fetch(job_id, connection=redis_conn)
        job.cancel()
        
        logger.info(f"任务已取消: {job_id}")
        return True
    
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return False
