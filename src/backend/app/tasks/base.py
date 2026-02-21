"""
任务基类和状态定义
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待执行
    QUEUED = "queued"         # 已入队
    STARTED = "started"       # 正在执行
    FINISHED = "finished"     # 执行完成
    FAILED = "failed"         # 执行失败
    CANCELED = "canceled"     # 已取消


class TaskType(str, Enum):
    """任务类型枚举"""
    WORDCLOUD = "wordcloud"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    QUIZ_GENERATION = "quiz_generation"


@dataclass
class AsyncTask:
    """
    异步任务数据类
    
    用于表示任务的状态和结果。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.WORDCLOUD
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0                      # 进度百分比 0-100
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 任务输入参数
    input_data: Dict[str, Any] = field(default_factory=dict)
    
    # 用户和课程关联
    user_id: Optional[str] = None
    course_id: Optional[str] = None
    chapter_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "input_data": self.input_data,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "chapter_id": self.chapter_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AsyncTask":
        """从字典创建任务对象"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            task_type=TaskType(data.get("task_type", "wordcloud")),
            status=TaskStatus(data.get("status", "pending")),
            progress=data.get("progress", 0),
            result=data.get("result"),
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            input_data=data.get("input_data", {}),
            user_id=data.get("user_id"),
            course_id=data.get("course_id"),
            chapter_id=data.get("chapter_id"),
        )
