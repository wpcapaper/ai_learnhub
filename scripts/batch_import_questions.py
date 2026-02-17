"""
批量导入题目脚本
自动扫描 data/output 目录下的题目 JSON 文件，并根据文件名自动推断课程代码进行批量导入。

使用方法:
    python scripts/batch_import_questions.py

文件名格式要求:
    {course_code}_{chapter_name}_questions.json
    例如: python_basics_01_变量与数据类型_questions.json

注意: 如果你的课程不在 KNOWN_COURSES 列表中，请先在下方添加课程代码！
"""
import os
import sys
import glob
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / ".." / "src" / "backend"))
os.chdir(project_root / ".." / "src" / "backend")

from app.core.database import SessionLocal
from import_questions import import_questions_from_json

def main():
    output_dir = Path(__file__).parent / "data" / "output"
    if not output_dir.exists():
        print(f"Error: Output directory not found at {output_dir}")
        return

    # 获取所有 json 文件
    json_files = sorted(glob.glob(str(output_dir / "*_questions.json")))
    
    if not json_files:
        print("No question files found to import.")
        return

    print(f"Found {len(json_files)} question files.")
    
    # 建立数据库会话
    db = SessionLocal()
    
    try:
        # 按课程分组文件
        course_files = {}
        for file_path in json_files:
            filename = Path(file_path).name
            # 假设文件名格式: {course_code}_{chapter_name}_questions.json
            # 我们需要一种策略来提取 course_code。
            # 由于 course_code 可能包含下划线，这里采用最长匹配法或目录匹配法。
            # 简单起见，我们假设 course_code 是第一个部分（但这对于 agent_development_tutorial 不适用）。
            
            # 更好的策略：根据已有的课程列表来匹配
            # 这里我们简化处理，硬编码已知课程的前缀逻辑，或者让用户确认。
            
            # ═══════════════════════════════════════════════════════════════
            # 🔧 已知课程列表 - 如果你的课程不在这里，请添加课程代码！
            # ═══════════════════════════════════════════════════════════════
            # 格式: 课程代码必须与数据库中 courses 表的 code 字段一致
            # 添加新课程: 直接在下方列表中添加课程代码字符串
            # ═══════════════════════════════════════════════════════════════
            KNOWN_COURSES = [
                "agent_development_tutorial",   # Agent 开发教程
                "langchain_introduction",       # LangChain 入门
                "rag_system_practical_guide",   # RAG 系统实战指南
                "python_basics",                # Python 基础
                # 👆 在这里添加你的课程代码，例如:
                # "your_new_course_code",
            ]
            # ═══════════════════════════════════════════════════════════════
            
            matched_course = None
            for course in KNOWN_COURSES:
                if filename.startswith(course):
                    matched_course = course
                    break
            
            if matched_course:
                if matched_course not in course_files:
                    course_files[matched_course] = []
                course_files[matched_course].append(file_path)
            else:
                print(f"⚠️  Skipping file (unknown course): {filename}")

        # 执行导入
        for course_code, files in course_files.items():
            print(f"\n🚀 Importing {len(files)} files for course: {course_code}")
            
            total_imported = 0
            for json_file in files:
                print(f"   Processing: {Path(json_file).name}")
                try:
                    result = import_questions_from_json(
                        json_file,
                        db,
                        course_code=course_code,
                        update_existing=True
                    )
                    total_imported += result['imported']
                except Exception as e:
                    print(f"   ❌ Error importing {Path(json_file).name}: {e}")
            
            print(f"✅ Finished {course_code}: {total_imported} questions imported.")

    finally:
        db.close()

if __name__ == "__main__":
    main()