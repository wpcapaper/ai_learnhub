"""
题目生成服务

基于课程内容使用 LLM 自动生成选择题，支持：
- 单章节题目生成
- 批量章节处理
- 直接保存到数据库
- 可选导出 JSON 文件

设计说明：
- 使用 app.llm 封装的 LLM 客户端
- 支持后台任务执行
- 支持 Langfuse 追踪
"""

import json
import logging
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.llm import get_llm_client, LLMError
from app.models import Question, Course

logger = logging.getLogger(__name__)


# 系统提示词（从原始脚本迁移）
SYSTEM_PROMPT = """你是一个专业的教育出题专家。请根据用户提供的课程内容，生成相关的单项选择题。
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
    "correct_answer": "A",
    "explanation": "答案解析",
    "difficulty": 1,
    "knowledge_points": ["知识点1", "知识点2"]
}

要求：
1. 题目要有针对性，考察课程中的核心概念。
2. 选项要有干扰性。
3. 生成 3-5 道题目。
4. 返回仅仅是一个 JSON 数组。
"""


@dataclass
class GeneratedQuestion:
    """生成的题目数据结构"""
    content: str
    question_type: str = "single_choice"
    options: Dict[str, str] = None
    correct_answer: str = ""
    explanation: str = ""
    difficulty: int = 2
    knowledge_points: List[str] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}
        if self.knowledge_points is None:
            self.knowledge_points = []
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "question_type": self.question_type,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "difficulty": self.difficulty,
            "knowledge_points": self.knowledge_points,
        }


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    course_code: str
    chapter_file: Optional[str]
    questions: List[GeneratedQuestion]
    error: Optional[str] = None
    tokens_used: Optional[Dict[str, int]] = None


class QuestionGenerationService:
    """
    题目生成服务
    
    核心功能：
    1. 从 markdown_courses/ 读取课程内容
    2. 使用 LLM 生成选择题
    3. 保存到数据库
    4. 可选导出 JSON 文件
    """
    
    # 配置常量
    MAX_CONTENT_LENGTH = 4000  # 最大内容长度（字符）
    DEFAULT_QUESTIONS_PER_CHAPTER = 5  # 每章节默认生成题目数
    
    def __init__(self, markdown_courses_dir: str = None):
        """
        初始化题目生成服务
        
        Args:
            markdown_courses_dir: markdown_courses 目录路径
        """
        if markdown_courses_dir:
            self.courses_dir = Path(markdown_courses_dir)
        else:
            # 默认路径
            docker_path = Path("/app/markdown_courses")
            if docker_path.exists():
                self.courses_dir = docker_path
            else:
                self.courses_dir = Path(__file__).parent.parent.parent.parent.parent / "markdown_courses"
        
        self._llm_client = None
    
    @property
    def llm_client(self):
        """延迟初始化 LLM 客户端"""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client
    
    def _compute_content_hash(self, content: str) -> str:
        """计算内容哈希（用于幂等性检查）"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    
    def _clean_llm_response(self, content: str) -> str:
        """清理 LLM 响应中的 Markdown 标记"""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
    
    def generate_questions_for_text(
        self,
        text: str,
        context_info: str = "",
        temperature: float = 0.7,
    ) -> List[GeneratedQuestion]:
        """
        使用 LLM 为文本内容生成题目
        
        Args:
            text: 课程内容文本
            context_info: 上下文信息（用于日志）
            temperature: LLM 温度参数
            
        Returns:
            生成的题目列表
        """
        # 截取内容避免超长
        truncated_text = text[:self.MAX_CONTENT_LENGTH]
        if len(text) > self.MAX_CONTENT_LENGTH:
            logger.warning(f"内容过长，已截取前 {self.MAX_CONTENT_LENGTH} 字符")
        
        logger.info(f"正在生成题目: {context_info}")
        
        try:
            # 使用同步客户端（适用于后台任务）
            response = self.llm_client.chat_sync(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"【课程内容】\n{truncated_text}"},
                ],
                temperature=temperature,
            )
            
            # 清理响应
            cleaned_content = self._clean_llm_response(response.content)
            
            # 解析 JSON
            questions_data = json.loads(cleaned_content)
            
            # 转换为 GeneratedQuestion 对象
            questions = []
            for q_data in questions_data:
                try:
                    question = GeneratedQuestion(
                        content=q_data.get("content", ""),
                        question_type=q_data.get("question_type", "single_choice"),
                        options=q_data.get("options", {}),
                        correct_answer=q_data.get("correct_answer", ""),
                        explanation=q_data.get("explanation", ""),
                        difficulty=q_data.get("difficulty", 2),
                        knowledge_points=q_data.get("knowledge_points", []),
                    )
                    questions.append(question)
                except Exception as e:
                    logger.warning(f"解析题目失败: {e}, 数据: {q_data}")
            
            logger.info(f"生成题目完成: {context_info}, 共 {len(questions)} 题")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            raise ValueError(f"LLM 返回的 JSON 格式无效: {e}")
        except LLMError as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
        except Exception as e:
            logger.error(f"生成题目失败: {e}")
            raise
    
    def generate_for_chapter(
        self,
        course_code: str,
        chapter_file: str,
    ) -> GenerationResult:
        """
        为单个章节生成题目
        
        Args:
            course_code: 课程代码（目录名）
            chapter_file: 章节文件名（相对路径）
            
        Returns:
            GenerationResult 生成结果
        """
        course_dir = self.courses_dir / course_code
        chapter_path = course_dir / chapter_file
        
        if not chapter_path.exists():
            return GenerationResult(
                success=False,
                course_code=course_code,
                chapter_file=chapter_file,
                questions=[],
                error=f"章节文件不存在: {chapter_path}",
            )
        
        try:
            # 读取章节内容
            content = chapter_path.read_text(encoding='utf-8')
            
            if len(content.strip()) < 100:
                return GenerationResult(
                    success=False,
                    course_code=course_code,
                    chapter_file=chapter_file,
                    questions=[],
                    error="内容过短，跳过生成",
                )
            
            # 生成题目
            context_info = f"{course_code} - {chapter_file}"
            questions = self.generate_questions_for_text(content, context_info)
            
            return GenerationResult(
                success=True,
                course_code=course_code,
                chapter_file=chapter_file,
                questions=questions,
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                course_code=course_code,
                chapter_file=chapter_file,
                questions=[],
                error=str(e),
            )
    
    def generate_for_course(
        self,
        course_code: str,
        chapter_files: List[str] = None,
    ) -> List[GenerationResult]:
        """
        为课程批量生成题目
        
        Args:
            course_code: 课程代码（目录名）
            chapter_files: 指定章节文件列表，为 None 时处理所有章节
            
        Returns:
            每个章节的生成结果列表
        """
        course_dir = self.courses_dir / course_code
        
        if not course_dir.exists():
            raise ValueError(f"课程目录不存在: {course_code}")
        
        # 读取 course.json 获取章节列表
        course_json_path = course_dir / "course.json"
        if not course_json_path.exists():
            raise ValueError(f"course.json 不存在: {course_code}")
        
        with open(course_json_path, 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        
        # 确定要处理的章节
        if chapter_files:
            chapters_to_process = [
                ch for ch in course_json.get("chapters", [])
                if ch.get("file") in chapter_files
            ]
        else:
            chapters_to_process = course_json.get("chapters", [])
        
        results = []
        for chapter_info in chapters_to_process:
            chapter_file = chapter_info.get("file")
            if not chapter_file:
                continue
            
            result = self.generate_for_chapter(course_code, chapter_file)
            results.append(result)
        
        return results
    
    def save_to_database(
        self,
        db: Session,
        course_id: str,
        questions: List[GeneratedQuestion],
        source_file: str = None,
        model: str = None,
    ) -> List[Question]:
        """
        将生成的题目保存到数据库
        
        Args:
            db: 数据库会话
            course_id: 课程 ID（数据库主键）
            questions: 生成的题目列表
            source_file: 来源文件名（用于元数据）
            model: 使用的模型名称
            
        Returns:
            保存的 Question 对象列表
        """
        saved_questions = []
        
        for q in questions:
            # 生成唯一 ID
            question_id = str(uuid.uuid4())
            
            # 创建 Question 对象
            question = Question(
                id=question_id,
                course_id=course_id,
                question_type=q.question_type,
                content=q.content,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                knowledge_points=q.knowledge_points,
                difficulty=q.difficulty,
                extra_data={
                    "source_file": source_file,
                    "generated_by": model or self.llm_client.default_model,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            )
            
            db.add(question)
            saved_questions.append(question)
        
        db.commit()
        logger.info(f"已保存 {len(saved_questions)} 道题目到数据库")
        
        return saved_questions
    
    def export_to_json(
        self,
        questions: List[GeneratedQuestion],
        output_path: Path,
        course_code: str,
        chapter_file: str,
    ) -> Path:
        """
        导出题目为 JSON 文件（兼容原有脚本格式）
        
        Args:
            questions: 生成的题目列表
            output_path: 输出目录
            course_code: 课程代码
            chapter_file: 章节文件名
            
        Returns:
            输出文件路径
        """
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        chapter_stem = Path(chapter_file).stem
        output_filename = f"{course_code}_{chapter_stem}_questions.json"
        output_file = output_path / output_filename
        
        # 转换为字典列表
        questions_data = [q.to_dict() for q in questions]
        
        # 添加元数据
        for q_data in questions_data:
            q_data["metadata"] = {
                "source_file": chapter_file,
                "generated_by": self.llm_client.default_model,
            }
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"题目已导出到: {output_file}")
        return output_file


def generate_quiz_for_course(
    course_code: str,
    db: Session = None,
    export_json: bool = False,
    output_dir: Path = None,
    chapter_files: Optional[List[str]] = None,
    markdown_courses_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    为课程生成题目的便捷函数（用于后台任务）
    
    Args:
        course_code: 课程代码（markdown_courses 目录名）
        db: 数据库会话，为 None 时不保存到数据库
        export_json: 是否导出 JSON 文件
        output_dir: JSON 输出目录
        chapter_files: 指定章节文件列表，为 None 时处理所有章节
        markdown_courses_dir: markdown_courses 目录路径，为 None 时自动检测
        
    Returns:
        生成结果统计
    """
    service = QuestionGenerationService(markdown_courses_dir)
    
    # 获取课程 ID
    course_id = None
    if db:
        course = db.query(Course).filter(Course.code == course_code).first()
        if course:
            course_id = course.id
        else:
            logger.warning(f"课程未在数据库中找到: {course_code}")
    
    # 生成题目
    results = service.generate_for_course(course_code, chapter_files=chapter_files)
    
    # 统计
    total_questions = 0
    chapters_processed = 0
    errors = []
    
    for result in results:
        if result.success:
            chapters_processed += 1
            total_questions += len(result.questions)
            
            # 保存到数据库
            if db and course_id and result.questions:
                service.save_to_database(
                    db=db,
                    course_id=course_id,
                    questions=result.questions,
                    source_file=result.chapter_file,
                )
            
            # 导出 JSON
            if export_json and result.questions:
                output_path = output_dir or Path("scripts/data/output")
                service.export_to_json(
                    questions=result.questions,
                    output_path=output_path,
                    course_code=course_code,
                    chapter_file=result.chapter_file,
                )
        else:
            errors.append(f"{result.chapter_file}: {result.error}")
    
    return {
        "success": len(errors) == 0,
        "course_code": course_code,
        "total_questions": total_questions,
        "chapters_processed": chapters_processed,
        "errors": errors,
    }
