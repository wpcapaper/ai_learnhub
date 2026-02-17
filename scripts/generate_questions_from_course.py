"""
根据课程内容生成题目脚本 (Producer)
读取 courses/ 目录下的 Markdown 文件，使用 DeepSeek 生成题目 JSON，
生成的 JSON 文件可直接被 import_questions.py (Consumer) 脚本使用。
"""
import os
import sys
import json
import asyncio
import glob
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 加载环境变量
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / 'src' / 'backend'
ENV_PATH = BACKEND_DIR / '.env'

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    print(f"Warning: .env file not found at {ENV_PATH}")

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

if not API_KEY:
    print("Error: LLM_API_KEY environment variable not set.")
    sys.exit(1)

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

OUTPUT_DIR = Path(__file__).parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = """
你是一个专业的教育出题专家。请根据用户提供的课程内容，生成相关的单项选择题。
输出必须是严格的 JSON 格式数组，不要包含 markdown 标记或其他文本。

每个题目的 JSON 结构如下：
{
    "content": "题目内容",
    "question_type": "single_choice",
    "options": {
        "A": "选项A内容",
        "B": "选项B内容",
        "C": "选项C内容",
        "D": "选项D内容"
    },
    "correct_answer": "A",  # 必须是选项的 Key (A, B, C, D)
    "explanation": "答案解析",
    "difficulty": 1,  # 1-3, 1为简单, 2为中等, 3为困难
    "knowledge_points": ["知识点1", "知识点2"]
}

要求：
1. 题目要有针对性，考察课程中的核心概念。
2. 选项要有干扰性。
3. 生成 3-5 道题目。
4. 返回仅仅是一个 JSON 数组。
"""

async def generate_questions_for_text(text: str, context_info: str) -> List[Dict]:
    """调用 LLM 生成题目"""
    print(f"   Generating questions for: {context_info}...")
    
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"【课程内容】\n{text[:4000]}..."} # 截取前4000字符避免超长
            ],
            stream=False
        )
        
        content = response.choices[0].message.content.strip()
        
        # 清理可能存在的 Markdown 代码块标记
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        return json.loads(content.strip())
        
    except Exception as e:
        print(f"   Error generating questions: {e}")
        return []

async def process_course_folder(course_dir: Path):
    """处理单个课程目录"""
    course_code = course_dir.name
    print(f"📦 Processing course: {course_code}")
    
    # 获取所有 Markdown 文件
    md_files = sorted(course_dir.glob("*.md"))
    
    if not md_files:
        print(f"   No markdown files found in {course_dir}")
        return

    total_generated = 0
    
    for md_file in md_files:
        # 跳过非章节文件
        if md_file.name.lower() in ['readme.md', 'summary.md']:
            continue
            
        print(f"   📄 Reading chapter: {md_file.name}")
        
        try:
            text_content = md_file.read_text(encoding='utf-8')
            if len(text_content.strip()) < 100:
                print("   Skipping: content too short")
                continue
                
            questions = await generate_questions_for_text(text_content, f"{course_code} - {md_file.name}")
            
            if questions:
                # 添加额外的元数据
                for q in questions:
                    q["metadata"] = {
                        "source_file": md_file.name,
                        "generated_by": "deepseek-v3"
                    }
                
                # 保存到输出目录
                output_filename = f"{course_code}_{md_file.stem}_questions.json"
                output_path = OUTPUT_DIR / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(questions, f, ensure_ascii=False, indent=2)
                
                print(f"   ✅ Saved {len(questions)} questions to {output_path.name}")
                total_generated += len(questions)
            else:
                print("   ⚠️ No questions generated")
                
        except Exception as e:
            print(f"   Error processing file {md_file.name}: {e}")

    print(f"🎉 Course {course_code} processing complete. Total questions: {total_generated}")

async def main():
    # 课程根目录
    courses_root = BASE_DIR / "courses"
    
    if not courses_root.exists():
        print(f"Error: Courses directory not found at {courses_root}")
        # 尝试 fallback 到 courses
        courses_root = BASE_DIR / "courses"
        if not courses_root.exists():
             print(f"Error: Neither 'learning_courses' nor 'courses' directory found.")
             return
        print(f"Fallback to: {courses_root}")

    # 遍历每个课程文件夹
    tasks = []
    for course_dir in courses_root.iterdir():
        if course_dir.is_dir() and not course_dir.name.startswith('.'):
            # 串行处理每个课程，避免并发过高
            await process_course_folder(course_dir)

if __name__ == "__main__":
    asyncio.run(main())