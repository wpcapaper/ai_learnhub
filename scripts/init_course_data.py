"""
课程数据初始化脚本（0-1阶段）
创建默认课程和考试配置

执行方式：
    cd scripts
    uv run python init_course_data.py

或使用 shell 脚本：
    cd scripts
    ./init_course_data.sh

说明：
    1. 脚本位于 scripts/ 目录
    2. 后端模块位于 src/backend/ 目录
    3. 脚本会自动添加后端目录到 Python 路径
    4. 脚本会自动切换工作目录到 src/backend/（确保相对路径正常工作）
"""
import sys
import os

# 添加后端目录到 Python 路径，以便导入 app.models 等模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

# 切换工作目录到后端目录，确保数据库相对路径正常工作
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

from sqlalchemy.orm import Session
from datetime import datetime

from app.models import Course, init_db
from app.core.database import engine
import secrets


def create_course(
    code: str,
    title: str,
    description: str,
    course_type: str = "exam",
    sort_order: int = 1,
    question_type_config: dict = None,
    difficulty_range: list = None,
    is_active: bool = True
) -> Course:
    """
    创建课程的通用构造函数

    Args:
        code: 课程代码
        title: 课程标题
        description: 课程描述
        course_type: 课程类型，默认 "exam"
        sort_order: 排序顺序
        question_type_config: 题型配置，默认 {"single_choice": 30, "multiple_choice": 10, "true_false": 10}
        difficulty_range: 难度范围，默认 [1, 5]
        is_active: 是否启用，默认 True

    Returns:
        Course: 课程对象
    """
    if question_type_config is None:
        question_type_config = {
            "single_choice": 30,
            "multiple_choice": 10,
            "true_false": 10
        }
    if difficulty_range is None:
        difficulty_range = [1, 5]

    return Course(
        id=secrets.token_hex(16),
        code=code,
        title=title,
        course_type=course_type,
        description=description,
        cover_image=None,
        default_exam_config={
            "question_type_config": question_type_config,
            "difficulty_range": difficulty_range
        },
        is_active=is_active,
        sort_order=sort_order,
        created_at=datetime.utcnow(),
        is_deleted=False
    )


def init_course_data(db: Session):
    """
    初始化课程数据 - 0-1阶段（无历史数据）

    创建默认课程：
    1. LLM基础知识 (llm_basic)
    2. AI认证考试 (ai_cert_exam)
    3. 机器学习认证考试 (ml_cert_exam)
    """
    courses = [
        create_course(
            code="llm_basic",
            title="AI认证考试",
            description="datawhale LLM基础知识题库",
            sort_order=1
        ),
        create_course(
            code="ai_cert_exam",
            title="AI认证考试",
            description="AI认证考试题库",
            sort_order=2
        ),
        create_course(
            code="ml_cert_exam",
            title="机器学习认证考试",
            description="机器学习认证考试题库",
            sort_order=3
        ),
    ]

    for course in courses:
        db.add(course)

    db.commit()
    print(f"✅ Created {len(courses)} courses:")
    for course in courses:
        print(f"   - {course.code}: {course.title}")


def main():
    """
    主函数：初始化课程数据
    """
    from app.core.database import SessionLocal

    print("🚀 Initializing course data...")

    # 创建数据库表
    print("📋 Creating database tables...")
    init_db()

    # 初始化课程数据
    db = SessionLocal()
    try:
        init_course_data(db)
        print("✅ Course data initialization completed!")
    except Exception as e:
        print(f"❌ Error initializing course data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
