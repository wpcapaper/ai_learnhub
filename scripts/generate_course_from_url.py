import os
import sys
import json
import asyncio
import re
import requests
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 尝试导入 BeautifulSoup
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("Warning: beautifulsoup4 not found. HTML parsing will be limited.")

# 加载环境变量
# 假设脚本位于 scripts/ 目录，.env 位于 src/backend/ 目录
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / 'src' / 'backend'
ENV_PATH = BACKEND_DIR / '.env'

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"Loaded environment from {ENV_PATH}")
else:
    print(f"Warning: .env file not found at {ENV_PATH}")

# 配置 OpenAI 客户端
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

if not API_KEY:
    print("Error: DEEPSEEK_API_KEY environment variable not set.")
    sys.exit(1)

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

def clean_html(html_content: str) -> str:
    """清理 HTML 内容，提取主要文本"""
    if not HAS_BS4:
        # 简单的正则清理
        text = re.sub(r'<[^>]+>', '', html_content)
        return "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 移除脚本、样式、导航、页脚、侧边栏、引用、编辑链接等无关内容
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "sup", "noscript", "iframe"]):
        element.decompose()
        
    # 针对维基百科等网站的特殊处理：移除 "mw-editsection" (编辑按钮), "reflist" (参考文献), "infobox" (信息框，可选保留)
    for class_name in ["mw-editsection", "reflist", "reference", "site-notice", "mw-jump-link"]:
        for element in soup.find_all(class_=class_name):
            element.decompose()

    # 提取主要内容区域 (针对维基百科是 'mw-content-text'，其他网站通常是 'main', 'article', 'content')
    main_content = soup.find(id="mw-content-text") or soup.find("main") or soup.find("article") or soup.body
    
    if not main_content:
        main_content = soup.body

    # 获取文本，保留一定的结构
    # 我们只提取特定的标签文本，以保持内容的纯净度
    content_lines = []
    for element in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'pre', 'code', 'table']):
        text = element.get_text().strip()
        if text:
            # 简单的格式保留
            if element.name.startswith('h'):
                content_lines.append(f"\n# {text}\n")
            elif element.name == 'ul' or element.name == 'ol':
                # 列表项单独处理会更精细，这里简化处理
                content_lines.append(f"{text}\n")
            else:
                content_lines.append(f"{text}\n")
    
    return "\n".join(content_lines)

async def fetch_url_content(url: str) -> str:
    """获取 URL 内容"""
    print(f"Fetching content from: {url}")
    # 添加 User-Agent 伪装成浏览器，避免被维基百科等网站拦截 (403 Forbidden)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return clean_html(response.text)
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None

async def generate_course_outline(content: str) -> Dict[str, Any]:
    """Phase 1: Generate course outline (metadata + chapter list) without full content"""
    print("Phase 1: Generating course outline...")

    system_prompt = """
    You are an expert Course Curator. Your task is to analyze the provided text and plan a structured learning course.
    
    IMPORTANT: Output MUST be in SIMPLIFIED CHINESE (简体中文).
    
    Output a strictly valid JSON object with this structure:
    {
        "code": "unique_slug_code",
        "title": "Course Title (Chinese)",
        "description": "Course Description (Chinese)",
        "cover_image": "https://placehold.co/600x400?text=Course+Cover", 
        "chapters": [
            {
                "title": "Chapter Title (Chinese)",
                "file": "01_chapter_slug.md",
                "summary": "Brief description of what this chapter covers (used for context)"
            }
        ]
    }
    
    Rules:
    1. 'code' should be lowercase, using underscores (e.g., 'python_basics').
    2. Divide content into 5-10 logical chapters for depth.
    3. JSON only, no markdown formatting.
    """

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Plan a course based on this content (first 20k chars):\n\n{content[:20000]}..."}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(result)
    except Exception as e:
        print(f"Error generating outline: {e}")
        return None

async def generate_chapter_content(chapter_title: str, chapter_summary: str, full_content: str) -> str:
    """Phase 2: Generate detailed content for a specific chapter"""
    print(f"Phase 2: Generating content for chapter '{chapter_title}'...")
    
    system_prompt = f"""
    You are an expert Course Curator writing a specific chapter for a course.
    
    Target Chapter: "{chapter_title}"
    Chapter Goal: {chapter_summary}
    
    Task: Write a DETAILED, COMPREHENSIVE educational tutorial for this chapter based on the Source Content.
    
    Requirements:
    1. Language: SIMPLIFIED CHINESE (简体中文).
    2. Format: Standard Markdown.
    3. Structure: Use H2 (##) for main sections, bullet points, and code blocks where relevant.
    4. Depth: Do not summarize. Explain concepts fully with examples from the source.
    5. Length: Aim for 1000+ words if source material supports it.
    """

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Source Content:\n\n{full_content[:40000]}"} # Increase context limit
            ],
            temperature=0.4,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating chapter content: {e}")
        return f"# {chapter_title}\n\n(Content generation failed. Please check logs.)"


def save_course(course_data: Dict[str, Any], output_root: Path):
    """保存课程文件"""
    course_slug = course_data.get("code")
    if not course_slug:
        print("Error: No course code found in data.")
        return

    course_dir = output_root / course_slug
    course_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created course directory: {course_dir}")

    # 1. 保存 course.json (不包含 content 字段)
    meta_data = {k: v for k, v in course_data.items() if k != "chapters"}
    
    # 处理章节元数据
    chapters_meta = []
    chapters_data = course_data.get("chapters", [])
    
    for chapter in chapters_data:
        chapters_meta.append({
            "title": chapter.get("title"),
            "file": chapter.get("file"),
            "sort_order": chapter.get("sort_order")
        })
        
        # 2. 保存章节 Markdown 文件
        file_name = chapter.get("file")
        content = chapter.get("content", "")
        
        # 确保文件名以 .md 结尾
        if not file_name.endswith('.md'):
            file_name += '.md'
            
        file_path = course_dir / file_name
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved chapter: {file_name}")

    meta_data["chapters"] = chapters_meta
    
    with open(course_dir / "course.json", 'w', encoding='utf-8') as f:
        json.dump(meta_data, f, indent=2, ensure_ascii=False)
    print("Saved course.json")

    return course_dir

async def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_course_from_url.py <URL or Text File Path>")
        print("Example: python generate_course_from_url.py https://en.wikipedia.org/wiki/Python_(programming_language)")
        sys.exit(1)
    
    input_source = sys.argv[1]
    content = ""
    
    # 判断是 URL 还是文件
    if input_source.startswith(('http://', 'https://')):
        content = await fetch_url_content(input_source)
    elif Path(input_source).exists():
        file_path = Path(input_source)
        print(f"Reading file: {file_path}")
        
        # 针对 .ipynb 文件的特殊处理
        if file_path.suffix.lower() == '.ipynb':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    notebook = json.load(f)
                    
                lines = []
                for cell in notebook.get('cells', []):
                    cell_type = cell.get('cell_type')
                    source = cell.get('source', [])
                    if isinstance(source, list):
                        source_text = ''.join(source)
                    else:
                        source_text = str(source)
                        
                    if cell_type == 'markdown':
                        lines.append(source_text)
                    elif cell_type == 'code':
                        lines.append(f"```python\n{source_text}\n```")
                
                content = "\n\n".join(lines)
                print(f"Successfully parsed notebook. Extracted {len(content)} chars.")
            except Exception as e:
                print(f"Error parsing .ipynb file: {e}")
                sys.exit(1)
        else:
            # 普通文本文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
    else:
        print("Error: Input is neither a valid URL nor an existing file.")
        sys.exit(1)
        
    if not content:
        print("Failed to get content. Exiting.")
        sys.exit(1)
        
    course_outline = await generate_course_outline(content)
    
    if course_outline:
        # Phase 2: Iterate and fill content
        final_chapters = []
        chapters = course_outline.get("chapters", [])
        total_chapters = len(chapters)
        
        print(f"\nCourse Outline Generated: '{course_outline.get('title')}' with {total_chapters} chapters.")
        print("Starting detailed content generation (this may take a while)...\n")
        
        for i, chapter in enumerate(chapters, 1):
            title = chapter.get("title")
            summary = chapter.get("summary", "")
            print(f"[{i}/{total_chapters}] Generating: {title}...")
            
            # Generate detailed content
            detailed_content = await generate_chapter_content(title, summary, content)
            
            # Update chapter object
            chapter["content"] = detailed_content
            chapter["sort_order"] = i # Ensure sort order
            final_chapters.append(chapter)
            
        course_outline["chapters"] = final_chapters
        
        # 输出目录：scripts/../learning_courses
        # 用户特别要求输出到 learning_courses/ 目录
        output_root = BASE_DIR / 'learning_courses'
        
        # 如果 learning_courses 不存在，尝试 courses (为了兼容性)，或者直接创建 learning_courses
        if not output_root.exists():
            output_root.mkdir(exist_ok=True)
            
        saved_dir = save_course(course_outline, output_root)
        
        print("\n" + "="*50)
        print(f"✅ Course generation complete!")
        print(f"📁 Course Location: {saved_dir}")
        print("="*50)
        print("\n👇 下一步操作:")
        print("1. 请检查上述文件夹中生成的 Markdown 文件。")
        print("2. 使用以下命令将课程导入数据库：")
        print(f'   python scripts/import_learning_courses.py "{output_root}"')
        print("\n   (注意：此命令将扫描并导入该文件夹下的所有课程)")
        
    else:
        print("Failed to generate course structure.")

if __name__ == "__main__":
    asyncio.run(main())