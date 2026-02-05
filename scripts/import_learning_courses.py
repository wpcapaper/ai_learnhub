"""
导入学习课程脚本

从 /courses 目录导入学习课程及其章节到数据库
"""
import os
import sys
import json
import uuid
from pathlib import Path

# 添加后端目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

# 切换工作目录到后端目录，确保相对路径正常工作
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import DATABASE_URL
from app.models import Course, Chapter, Base


def import_learning_courses(courses_dir: str = None):
    """
    导入学习课程到数据库

    Args:
        courses_dir: 课程目录路径，默认为 /courses

    Returns:
        dict: 导入统计信息
    """
    # 设置课程目录路径
    if courses_dir is None:
        courses_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "courses")
    courses_dir = os.path.abspath(courses_dir)

    print(f"📁 扫描课程目录: {courses_dir}")

    # 创建数据库引擎和会话
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)

    statistics = {
        "scanned_courses": 0,
        "imported_courses": 0,
        "imported_chapters": 0,
        "skipped_courses": 0,
        "errors": []
    }

    try:
        # 扫描课程目录
        for course_folder in os.listdir(courses_dir):
            course_path = os.path.join(courses_dir, course_folder)

            # 跳过非目录
            if not os.path.isdir(course_path):
                continue

            # 跳过隐藏目录
            if course_folder.startswith('.'):
                continue

            statistics["scanned_courses"] += 1

            try:
                # 读取 course.json
                course_json_path = os.path.join(course_path, "course.json")
                if not os.path.exists(course_json_path):
                    print(f"⚠️  跳过 {course_folder}: 未找到 course.json")
                    statistics["skipped_courses"] += 1
                    continue

                with open(course_json_path, 'r', encoding='utf-8') as f:
                    course_data = json.load(f)

                # 检查课程是否已存在
                existing_course = db.query(Course).filter(
                    Course.code == course_data.get("code")
                ).first()

                if existing_course:
                    print(f"⚠️  跳过 {course_folder}: 课程代码已存在")
                    statistics["skipped_courses"] += 1
                    continue

                # 创建课程
                course = Course(
                    id=str(uuid.uuid4()),
                    code=course_data.get("code"),
                    title=course_data.get("title"),
                    description=course_data.get("description"),
                    course_type="learning",  # 强制为 learning 类型
                    cover_image=course_data.get("cover_image"),
                    default_exam_config=course_data.get("default_exam_config"),
                    is_active=True,
                    sort_order=course_data.get("sort_order", 0)
                )

                db.add(course)
                db.flush()  # 刷新以获取 course.id

                print(f"✅ 导入课程: {course.title}")

                # 导入章节
                chapters = course_data.get("chapters", [])
                for chapter_info in chapters:
                    chapter_file = chapter_info.get("file")
                    chapter_file_path = os.path.join(course_path, chapter_file)

                    if not os.path.exists(chapter_file_path):
                        print(f"  ⚠️  跳过章节 {chapter_file}: 文件不存在")
                        statistics["errors"].append(f"{course_folder}/{chapter_file}: 文件不存在")
                        continue

                    # 读取 markdown 内容
                    with open(chapter_file_path, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()

                    # 创建章节
                    chapter = Chapter(
                        id=str(uuid.uuid4()),
                        course_id=course.id,
                        title=chapter_info.get("title"),
                        content_markdown=markdown_content,
                        sort_order=chapter_info.get("sort_order", 0)
                    )

                    db.add(chapter)
                    print(f"  ✅ 导入章节: {chapter_info.get('title')}")
                    statistics["imported_chapters"] += 1

                # 提交更改
                db.commit()
                statistics["imported_courses"] += 1

            except Exception as e:
                print(f"❌ 导入 {course_folder} 失败: {str(e)}")
                statistics["errors"].append(f"{course_folder}: {str(e)}")
                db.rollback()
                continue

    except Exception as e:
        print(f"❌ 导入过程发生错误: {str(e)}")
        statistics["errors"].append(f"全局错误: {str(e)}")

    finally:
        db.close()

    # 打印统计信息
    print("\n" + "="*50)
    print("📊 导入统计")
    print("="*50)
    print(f"扫描课程数: {statistics['scanned_courses']}")
    print(f"导入课程数: {statistics['imported_courses']}")
    print(f"跳过课程数: {statistics['skipped_courses']}")
    print(f"导入章节数: {statistics['imported_chapters']}")
    print(f"错误数: {len(statistics['errors'])}")

    if statistics['errors']:
        print("\n❌ 错误列表:")
        for error in statistics['errors']:
            print(f"  - {error}")

    print("="*50 + "\n")

    return statistics


def main():
    """
    主函数
    """
    print("🚀 开始导入学习课程...\n")

    # 从命令行参数获取课程目录（可选）
    courses_dir = None
    if len(sys.argv) > 1:
        courses_dir = sys.argv[1]

    # 执行导入
    statistics = import_learning_courses(courses_dir)

    # 根据结果返回退出码
    if statistics['errors']:
        sys.exit(1)
    else:
        print("✅ 导入完成！")
        sys.exit(0)


if __name__ == "__main__":
    main()
