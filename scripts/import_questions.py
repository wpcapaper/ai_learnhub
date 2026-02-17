"""
题目导入脚本（修改版 - 支持课程和题集）
将题目JSON文件导入到指定课程，可选创建固定题集
"""
import sys
import json
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / ".." / "src" / "backend"))

# Change to backend directory so relative paths work
os.chdir(project_root / ".." / "src" / "backend")

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Course, QuestionSet, Question, init_db
import secrets
from datetime import datetime


def import_questions_from_json(
    json_file: str,
    db: Session,
    course_code: str,
    question_set_code: str = None,
    question_set_name: str = None,
    update_existing: bool = False
):
    """
    从JSON文件导入题目到指定课程，可选创建固定题集

    Args:
        json_file: JSON文件路径
        db: 数据库会话
        course_code: 课程代码（必需）
        question_set_code: 题集代码（可选）
        question_set_name: 题集名称（可选）

    Returns:
        dict: 导入统计
    """
    # 查找课程（必须存在，不支持自动创建）
    course = db.query(Course).filter(
        Course.code == course_code
    ).first()

    if not course:
        raise ValueError(f"Course not found: {course_code}. Please run init_course_data.py first.")

    # 读取JSON文件
    with open(json_file, 'r', encoding='utf-8') as f:
        questions_data = json.load(f)

    # 支持单个题目或题目列表
    if isinstance(questions_data, dict):
        questions_list = [questions_data]
    elif isinstance(questions_data, list):
        questions_list = questions_data
    else:
        raise ValueError("JSON格式错误：期望对象或数组")

    imported = 0
    skipped = 0
    errors = []
    question_ids = []

    for q_data in questions_list:
        # 检查必填字段
        required_fields = ['question_type', 'content', 'correct_answer']
        missing_fields = [f for f in required_fields if f not in q_data]

        if missing_fields:
            errors.append(f"题目缺少必填字段: {', '.join(missing_fields)}")
            skipped += 1
            continue

        # 检查是否已存在（主要通过content判断，因为correct_answer可能会变格式）
        # 使用 content 的前50个字符进行模糊匹配查询，然后在内存中精确比对
        # 这样可以避免因 correct_answer 或 explanation 变更导致的重复插入
        
        # 转义 SQL LIKE 通配符，防止意外匹配
        def escape_like_pattern(text: str) -> str:
            """转义 SQL LIKE 通配符 % 和 _"""
            return text.replace('%', r'\%').replace('_', r'\_')
        
        content_prefix = q_data['content'][:50]
        escaped_prefix = escape_like_pattern(content_prefix)
        
        potential_matches = db.query(Question).filter(
            Question.course_id == course.id,
            Question.content.like(f"{escaped_prefix}%", escape='\\')  # 使用 escape 参数
        ).all()
        
        existing = None
        for pm in potential_matches:
            # 精确比对 content (去除首尾空格)
            if pm.content.strip() == q_data['content'].strip():
                existing = pm
                break

        if existing:
            if update_existing:
                existing.options = q_data.get('options')
                existing.correct_answer = q_data['correct_answer']
                existing.explanation = q_data.get('explanation')
                if q_data.get('knowledge_points'):
                    existing.knowledge_points = q_data.get('knowledge_points')
                
                question_ids.append(existing.id)
                imported += 1
                print(f"  Updated existing question: {q_data['content'][:20]}...")
                continue
            else:
                skipped += 1
                continue

        # 创建题目对象
        question = Question(
            id=q_data.get('id', str(secrets.token_hex(16))),
            course_id=course.id,  # ✅ 使用course_id而非course_type
            question_type=q_data.get('question_type', 'single_choice'),
            content=q_data['content'],
            options=q_data.get('options'),
            correct_answer=q_data['correct_answer'],
            explanation=q_data.get('explanation'),
            knowledge_points=q_data.get('knowledge_points'),
            difficulty=q_data.get('difficulty', 2),
            question_set_ids=[],  # 初始化为空列表
            is_controversial=q_data.get('is_controversial', False),
            extra_data=q_data.get('metadata', {}),
            vector_id=q_data.get('vector_id'),
            created_at=datetime.utcnow()
        )

        db.add(question)
        db.flush()
        question_ids.append(question.id)
        imported += 1

    # 如果需要，创建固定题集
    if question_set_code and question_set_name and question_ids:
        # 检查题集是否已存在
        existing_set = db.query(QuestionSet).filter(
            QuestionSet.code == question_set_code
        ).first()

        if existing_set:
            # 如果题集已存在，更新它
            existing_ids = existing_set.fixed_question_ids or []
            existing_set.fixed_question_ids = existing_ids + question_ids
            existing_set.total_questions = len(existing_set.fixed_question_ids)
            print(f"✅ Updated question set: {question_set_name} with {len(question_ids)} new questions")
        else:
            # 创建新题集
            question_set = QuestionSet(
                id=secrets.token_hex(16),
                course_id=course.id,
                code=question_set_code,
                name=question_set_name,
                fixed_question_ids=question_ids,
                description=None,
                total_questions=len(question_ids),
                is_active=True,
                created_at=datetime.utcnow(),
                is_deleted=False
            )
            db.add(question_set)
            print(f"✅ Created question set: {question_set_name} with {len(question_ids)} questions")

        # 更新题目的question_set_ids
        if existing_set:
            # 如果更新现有题集，不需要更新question_set_ids（因为使用的是新的合并列表）
            pass
        else:
            for q_id in question_ids:
                question = db.query(Question).filter(Question.id == q_id).first()
                if question:
                    if question.question_set_ids is None:
                        question.question_set_ids = []
                    if question_set.id not in question.question_set_ids:
                        question.question_set_ids.append(question_set.id)

    # 提交所有更改
    db.commit()

    print(f"✅ Imported {imported} questions to course: {course.title} ({course_code})")
    if question_set_code:
        print(f"   Question set: {question_set_code}")

    return {
        "total": len(questions_list),
        "imported": imported,
        "skipped": skipped,
        "errors": len(errors),
        "error_details": errors[:10]  # 只返回前10个错误
    }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='导入题目到指定课程')
    parser.add_argument('--json-file', '-f', required=True, help='JSON文件路径（支持多文件），默认从 data/output/ 目录读取')
    parser.add_argument('--course-code', '-c', required=True, help='课程代码（如：ai_cert_exam）')
    parser.add_argument('--question-set-code', '-s', help='题集代码（可选，用于创建固定题集）')
    parser.add_argument('--question-set-name', '-n', help='题集名称（可选，用于创建固定题集）')
    parser.add_argument('--init-db', '-i', action='store_true', help='初始化数据库表')

    args = parser.parse_args()

    # 初始化数据库表
    if args.init_db:
        print("初始化数据库...")
        init_db()

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 处理文件路径：默认从 data/output/ 目录读取
        default_output_dir = Path(__file__).parent / "data" / "output"

        # 支持多文件导入
        json_files = args.json_file.split(',')
        json_files = [f.strip() for f in json_files]

        # 如果文件不是绝对路径且不以 data/output/ 开头，自动拼接
        for i, file_path in enumerate(json_files):
            path = Path(file_path)
            if not path.is_absolute() and not str(path).startswith("data/output/"):
                json_files[i] = str(default_output_dir / path)

        total_imported = 0
        total_skipped = 0

        for json_file in json_files:
            json_file = str(json_file)
            print(f"\n从 {json_file} 导入题目...")
            result = import_questions_from_json(
                json_file,
                db,
                args.course_code,
                args.question_set_code,
                args.question_set_name
            )

            total_imported += result['imported']
            total_skipped += result['skipped']

        # 打印结果
        print("\n导入完成！")
        total_result = {
            "total": result['total'] if 'result' in locals() else 0,
            "imported": total_imported,
            "skipped": total_skipped,
            "errors": result['errors'] if 'result' in locals() else 0,
            "error_details": result['error_details'] if 'result' in locals() else []
        }
        print(f"  总题目数: {total_result['total']}")
        print(f"  成功导入: {total_imported}")
        print(f"  跳过: {total_skipped}")
        print(f"  错误: {total_result['errors']}")

        if total_result['error_details']:
            print("\n错误详情（前10个）:")
            for error in total_result['error_details']:
                print(f"  - {error}")

    except Exception as e:
        print(f"\n错误: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
