"""
Models package
Export all database models
"""

from .base import Base
from .user import User
from .question import Question
from .record import UserLearningRecord
from .batch import QuizBatch, BatchAnswer
from .course import Course
from .question_set import QuestionSet
from .user_settings import UserSettings
from .conversation import Conversation, Message
from .user_course_progress import UserCourseProgress
from .answer_history import UserAnswerHistory
from .chapter import Chapter
from .reading_progress import ReadingProgress
from .chapter_kb_config import ChapterKBConfig

__all__ = [
    "Base",
    "User",
    "Question",
    "UserLearningRecord",
    "QuizBatch",
    "BatchAnswer",
    "Course",
    "QuestionSet",
    "UserSettings",
    "UserCourseProgress",
    "UserAnswerHistory",
    "Chapter",
    "ReadingProgress",
    "Conversation",
    "Message",
    "ChapterKBConfig",
]


def init_db():
    """初始化数据库"""
    from ..core.database import engine

    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def drop_all():
    """删除所有表（仅开发测试用）"""
    from ..core.database import engine

    # 删除所有表
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All tables dropped")
