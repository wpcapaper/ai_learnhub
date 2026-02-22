"""
课程转换管道 - 核心管道逻辑

该模块协调整个课程转换流程：
1. 扫描 raw_courses 目录
2. 转换各种格式的课程文件
3. 编排章节顺序
4. 执行质量评估
5. 输出到 markdown_courses/{name}_v{N}/ 目录

所有RAG相关数据独立存储，不依赖业务数据库（app.db）
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import shutil
import re
import time
from datetime import datetime

from .models import (
    RawCourse,
    ConvertedCourse,
    Chapter,
    QualityReport,
    ConversionResult,
    SourceFile,
    ContentType,
)
from .converters import ConverterRegistry
from .evaluators import (
    QualityEvaluator,
    EvaluationContext,
    save_quality_report,
    load_quality_report,
)


class ChapterSorter:
    """
    章节排序器
    
    自动检测和编排章节顺序，支持多种命名模式
    """
    
    # 常见的章节命名模式
    PATTERNS = [
        # 数字序号模式: 01_xxx, 1_xxx, 1-xxx
        (r'^(\d+)[-_]?(.*)$', 'numeric'),
        # 中文数字模式: 第一章, 第1章
        (r'^第([一二三四五六七八九十\d]+)章[:：\s]*(.*)$', 'chinese'),
        # 英文章节: Chapter 1, Ch.1
        (r'^[Cc]h(?:apter)?[.\s]*(\d+)[:：\s]*(.*)$', 'english'),
        # Part模式: Part 1, Part1
        (r'^[Pp]art\s*(\d+)[:：\s]*(.*)$', 'part'),
    ]
    
    @classmethod
    def sort_chapters(cls, chapters: List[Chapter]) -> List[Chapter]:
        """
        对章节进行排序
        
        Args:
            chapters: 章节列表
        
        Returns:
            排序后的章节列表
        """
        if not chapters:
            return chapters
        
        # 尝试提取排序信息
        sort_info = []
        for idx, chapter in enumerate(chapters):
            order = cls._extract_order(chapter)
            sort_info.append((order, idx, chapter))
        
        # 按提取的顺序排序，保持原始顺序作为后备
        sort_info.sort(key=lambda x: (x[0], x[1]))
        
        # 更新排序序号
        sorted_chapters = []
        for new_order, (_, _, chapter) in enumerate(sort_info, 1):
            chapter.sort_order = new_order
            sorted_chapters.append(chapter)
        
        return sorted_chapters
    
    @classmethod
    def _extract_order(cls, chapter: Chapter) -> tuple:
        """
        从章节标题或文件名中提取排序信息
        
        Returns:
            (主序号, 副序号, 标题) 用于排序比较
        """
        # 优先从文件名提取
        filename_order = cls._parse_filename(chapter.file_name)
        if filename_order:
            return filename_order
        
        # 从标题提取
        title_order = cls._parse_title(chapter.title)
        if title_order:
            return title_order
        
        # 使用原始sort_order
        return (chapter.sort_order, 0, chapter.title)
    
    @classmethod
    def _parse_filename(cls, filename: str) -> Optional[tuple]:
        """从文件名提取排序信息"""
        stem = Path(filename).stem
        
        for pattern, _ in cls.PATTERNS:
            match = re.match(pattern, stem)
            if match:
                num = cls._parse_number(match.group(1))
                title = match.group(2) if len(match.groups()) > 1 else stem
                return (num, 0, title)
        
        return None
    
    @classmethod
    def _parse_title(cls, title: str) -> Optional[tuple]:
        """从标题提取排序信息"""
        for pattern, _ in cls.PATTERNS:
            match = re.match(pattern, title)
            if match:
                num = cls._parse_number(match.group(1))
                subtitle = match.group(2) if len(match.groups()) > 1 else title
                return (num, 0, subtitle)
        
        return None
    
    @classmethod
    def _parse_number(cls, num_str: str) -> int:
        """解析数字（包括中文数字）"""
        chinese_nums = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        
        if num_str.isdigit():
            return int(num_str)
        
        if num_str in chinese_nums:
            return chinese_nums[num_str]
        
        # 处理 "十一"、"十二" 等
        if len(num_str) == 2 and num_str[0] == '十':
            return 10 + chinese_nums.get(num_str[1], 0)
        
        return 0


class CoursePipeline:
    """
    课程转换管道
    
    主入口类，协调整个转换流程
    
    输出目录结构：markdown_courses/{course_name}_v{N}/
    """
    
    def __init__(
        self,
        raw_courses_dir: str = "raw_courses",
        markdown_courses_dir: str = "markdown_courses",
        llm_client: Optional[Any] = None
    ):
        """
        初始化管道
        
        Args:
            raw_courses_dir: 原始课程目录
            markdown_courses_dir: 输出课程目录（转换后的 markdown）
            llm_client: 可选的LLM客户端（用于质量评估）
        """
        self.raw_courses_dir = Path(raw_courses_dir)
        self.markdown_courses_dir = Path(markdown_courses_dir)
        self.converter_registry = ConverterRegistry()
        self.quality_evaluator = QualityEvaluator(llm_client)
    
    def _get_next_version(self, course_id: str) -> int:
        """获取课程的下一个版本号"""
        pattern = f"{course_id}_v*"
        existing_versions = []
        
        if self.markdown_courses_dir.exists():
            for d in self.markdown_courses_dir.glob(pattern):
                if d.is_dir():
                    match = re.search(r'_v(\d+)$', d.name)
                    if match:
                        existing_versions.append(int(match.group(1)))
        
        return max(existing_versions) + 1 if existing_versions else 1
    
    def scan_raw_courses(self) -> List[RawCourse]:
        """
        扫描原始课程目录
        
        Returns:
            发现的原始课程列表
        """
        courses = []
        
        if not self.raw_courses_dir.exists():
            return courses
        
        for course_dir in self.raw_courses_dir.iterdir():
            if not course_dir.is_dir():
                continue
            
            # 跳过隐藏目录
            if course_dir.name.startswith('.'):
                continue
            
            # 收集支持的文件类型
            source_files = []
            for ext in ['*.md', '*.ipynb']:
                for file_path in course_dir.rglob(ext):
                    # 跳过隐藏文件和检查点文件
                    if '.ipynb_checkpoints' in str(file_path) or file_path.name.startswith('.'):
                        continue
                    source_files.append(SourceFile.from_path(str(file_path)))
            
            if source_files:
                # 提取课程名称（从目录名或课程标题文件）
                course_name = self._extract_course_name(course_dir)
                
                courses.append(RawCourse(
                    course_id=course_dir.name,
                    name=course_name,
                    source_dir=str(course_dir),
                    description=f"从 {course_dir.name} 目录导入",
                    source_files=source_files
                ))
        
        return courses
    
    def _copy_assets(self, source_dir: str, output_dir: Path) -> int:
        source_path = Path(source_dir)
        copied_count = 0
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico'}
        
        for file_path in source_path.rglob('*'):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in image_extensions:
                continue
            if '.ipynb_checkpoints' in str(file_path) or file_path.name.startswith('.'):
                continue
            
            rel_path = file_path.relative_to(source_path)
            dest_path = output_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_path)
            copied_count += 1
        
        return copied_count
    
    def convert_course(self, raw_course: RawCourse, version: Optional[int] = None) -> ConversionResult:
        """
        转换单个课程
        
        Args:
            raw_course: 原始课程数据
            version: 指定版本号（可选，不传则自动递增）
        
        Returns:
            转换结果
        """
        start_time = time.time()
        
        try:
            # 确定版本号
            if version is None:
                version = self._get_next_version(raw_course.course_id)
            
            # 1. 创建输出目录：markdown_courses/{course_id}_v{N}/
            output_dir_name = f"{raw_course.course_id}_v{version}"
            output_dir = self.markdown_courses_dir / output_dir_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 1.5 复制图片等资源文件
            self._copy_assets(raw_course.source_dir, output_dir)
            
            # 2. 转换所有源文件
            all_chapters = []
            for source_file in raw_course.source_files:
                converter = self.converter_registry.get_converter(source_file.content_type)
                if converter:
                    chapters = converter.convert(source_file, output_dir)
                    all_chapters.extend(chapters)
            
            if not all_chapters:
                return ConversionResult(
                    success=False,
                    error_message="没有成功转换任何章节"
                )
            
            # 3. 章节排序
            sorted_chapters = ChapterSorter.sort_chapters(all_chapters)
            
            # 4. 写入章节文件
            for chapter in sorted_chapters:
                chapter_path = output_dir / chapter.file_name
                with open(chapter_path, 'w', encoding='utf-8') as f:
                    f.write(chapter.content)
            
            # 5. 创建转换后的课程对象
            converted_course = ConvertedCourse(
                course_id=raw_course.course_id,
                code=self._generate_course_code(raw_course.course_id),
                title=raw_course.name,
                description=raw_course.description,
                chapters=sorted_chapters
            )
            
            # 6. 生成 course.json
            course_json_path = output_dir / "course.json"
            with open(course_json_path, 'w', encoding='utf-8') as f:
                json.dump(converted_course.to_course_json(), f, ensure_ascii=False, indent=2)
            
            # 7. 执行质量评估
            eval_context = EvaluationContext(
                course_id=raw_course.course_id,
                course_title=raw_course.name,
                chapters=sorted_chapters
            )
            quality_report = self.quality_evaluator.evaluate(eval_context)
            converted_course.quality_report = quality_report
            
            # 8. 保存质量报告（独立存储，不依赖数据库）
            save_quality_report(quality_report, output_dir)
            
            processing_time = time.time() - start_time
            
            return ConversionResult(
                success=True,
                course=converted_course,
                processing_time=processing_time,
                warnings=[f"处理了 {len(sorted_chapters)} 个章节"]
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def convert_all(self) -> List[ConversionResult]:
        """
        转换所有发现的课程
        
        Returns:
            所有转换结果列表
        """
        results = []
        raw_courses = self.scan_raw_courses()
        
        for raw_course in raw_courses:
            result = self.convert_course(raw_course)
            results.append(result)
        
        return results
    
    def _extract_course_name(self, course_dir: Path) -> str:
        """从课程目录提取课程名称"""
        # 尝试从目录名提取（去除序号前缀）
        dir_name = course_dir.name
        match = re.match(r'^\d+[._-]?(.+)$', dir_name)
        if match:
            return match.group(1).replace('_', ' ').replace('-', ' ')
        
        # 检查是否有 course.json 或 README
        for filename in ['course.json', 'README.md', 'readme.md']:
            path = course_dir / filename
            if path.exists():
                try:
                    if filename.endswith('.json'):
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'title' in data:
                                return data['title']
                            if 'name' in data:
                                return data['name']
                    else:
                        with open(path, 'r', encoding='utf-8') as f:
                            first_line = f.readline()
                            # 提取标题
                            title_match = re.match(r'^#\s+(.+)$', first_line)
                            if title_match:
                                return title_match.group(1).strip()
                except:
                    pass
        
        return dir_name
    
    def _generate_course_code(self, course_id: str) -> str:
        """生成课程代码（用于URL标识）"""
        # 清理ID，生成合适的代码
        code = re.sub(r'[^\w\u4e00-\u9fff-]', '_', course_id)
        code = re.sub(r'_+', '_', code).strip('_')
        return code.lower()


class RAGChunkOptimizer:
    """
    自适应RAG分块优化器
    
    在沙箱环境中测试不同的分块策略，找出最佳方案
    注意：完全独立于业务数据库运行
    """
    
    def __init__(self, rag_config: Optional[Dict[str, Any]] = None):
        """
        初始化优化器
        
        Args:
            rag_config: RAG配置（可选）
        """
        self.rag_config = rag_config or {}
    
    def test_chunk_strategies(
        self,
        content: str,
        test_queries: List[Dict[str, Any]],
        strategies: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        测试不同的分块策略
        
        Args:
            content: 课程内容
            test_queries: 测试查询列表，每个包含 query 和 expected_keywords
            strategies: 要测试的策略列表
        
        Returns:
            测试报告，包含各策略的召回率等指标
        """
        if strategies is None:
            strategies = self._get_default_strategies()
        
        results = {}
        
        for strategy in strategies:
            strategy_name = strategy.get("name", "unknown")
            
            # 在沙箱中执行分块
            chunks = self._apply_chunk_strategy(content, strategy)
            
            # 测试召回
            recall_scores = []
            for test_case in test_queries:
                query = test_case["query"]
                expected_keywords = test_case.get("expected_keywords", [])
                
                # 计算召回率
                recall = self._calculate_recall(chunks, query, expected_keywords)
                recall_scores.append(recall)
            
            avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0
            
            results[strategy_name] = {
                "avg_recall": avg_recall,
                "chunk_count": len(chunks),
                "avg_chunk_size": sum(len(c) for c in chunks) / len(chunks) if chunks else 0,
                "recall_scores": recall_scores,
                "strategy_config": strategy
            }
        
        # 找出最佳策略
        best_strategy = max(results.items(), key=lambda x: x[1]["avg_recall"])
        
        return {
            "strategy_results": results,
            "recommended_strategy": best_strategy[0],
            "recommended_config": best_strategy[1]["strategy_config"],
            "summary": f"推荐使用 {best_strategy[0]} 策略，平均召回率 {best_strategy[1]['avg_recall']:.2%}"
        }
    
    def _get_default_strategies(self) -> List[Dict[str, Any]]:
        """获取默认的分块策略列表"""
        return [
            {
                "name": "semantic_small",
                "type": "semantic",
                "min_chunk_size": 100,
                "max_chunk_size": 500,
                "overlap_size": 50
            },
            {
                "name": "semantic_medium",
                "type": "semantic",
                "min_chunk_size": 200,
                "max_chunk_size": 1000,
                "overlap_size": 100
            },
            {
                "name": "semantic_large",
                "type": "semantic",
                "min_chunk_size": 500,
                "max_chunk_size": 2000,
                "overlap_size": 200
            },
            {
                "name": "fixed_small",
                "type": "fixed",
                "chunk_size": 256,
                "overlap_size": 32
            },
            {
                "name": "fixed_medium",
                "type": "fixed",
                "chunk_size": 512,
                "overlap_size": 64
            },
            {
                "name": "heading_based",
                "type": "heading",
                "respect_structure": True,
                "max_chunk_size": 1500
            }
        ]
    
    def _apply_chunk_strategy(self, content: str, strategy: Dict[str, Any]) -> List[str]:
        """应用分块策略"""
        strategy_type = strategy.get("type", "semantic")
        
        if strategy_type == "fixed":
            return self._fixed_chunk(content, strategy)
        elif strategy_type == "heading":
            return self._heading_chunk(content, strategy)
        else:
            return self._semantic_chunk(content, strategy)
    
    def _fixed_chunk(self, content: str, strategy: Dict[str, Any]) -> List[str]:
        """固定大小分块"""
        chunk_size = strategy.get("chunk_size", 512)
        overlap = strategy.get("overlap_size", 50)
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            
            # 尝试在句子边界切分
            if end < len(content):
                for i in range(min(100, len(chunk) - 1)):
                    if chunk[-i-1] in '。！？\n':
                        chunk = content[start:end-i-1]
                        break
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - overlap
        
        return chunks
    
    def _semantic_chunk(self, content: str, strategy: Dict[str, Any]) -> List[str]:
        """语义分块（基于段落）"""
        min_size = strategy.get("min_chunk_size", 100)
        max_size = strategy.get("max_chunk_size", 1000)
        overlap = strategy.get("overlap_size", 100)
        
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', content)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 <= max_size:
                current_chunk += "\n\n" + para if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if len(para) > max_size:
                    # 段落太长，需要进一步分割
                    sub_chunks = self._fixed_chunk(para, {
                        "chunk_size": max_size,
                        "overlap_size": overlap
                    })
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # 合并过小的块
        merged_chunks = []
        for chunk in chunks:
            if len(chunk) < min_size and merged_chunks:
                last_chunk = merged_chunks[-1]
                if len(last_chunk) + len(chunk) + 2 <= max_size:
                    merged_chunks[-1] = last_chunk + "\n\n" + chunk
                    continue
            merged_chunks.append(chunk)
        
        return merged_chunks
    
    def _heading_chunk(self, content: str, strategy: Dict[str, Any]) -> List[str]:
        """基于标题的分块"""
        max_size = strategy.get("max_chunk_size", 1500)
        
        # 按二级标题分割（保持一级标题作为章节）
        sections = re.split(r'\n##\s+', content)
        
        chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            if len(section) <= max_size:
                chunks.append("## " + section if not section.startswith('#') else section)
            else:
                # 分割过长的节
                sub_chunks = self._semantic_chunk(section, {
                    "min_chunk_size": 100,
                    "max_chunk_size": max_size,
                    "overlap_size": 100
                })
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _calculate_recall(
        self,
        chunks: List[str],
        query: str,
        expected_keywords: List[str]
    ) -> float:
        """
        计算召回率（简化版本，基于关键词匹配）
        
        实际应用中应该使用真实的embedding和向量检索
        """
        if not expected_keywords:
            return 1.0
        
        # 简化的关键词匹配
        query_lower = query.lower()
        found_keywords = set()
        
        for keyword in expected_keywords:
            keyword_lower = keyword.lower()
            
            # 检查是否有chunk包含该关键词
            for chunk in chunks:
                if keyword_lower in chunk.lower():
                    found_keywords.add(keyword)
                    break
        
        recall = len(found_keywords) / len(expected_keywords)
        return recall
    
    def save_optimization_report(self, report: Dict[str, Any], output_path: Path):
        """保存优化报告"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report["generated_at"] = datetime.now().isoformat()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


def run_pipeline(
    raw_courses_dir: str = "raw_courses",
    markdown_courses_dir: str = "markdown_courses",
    llm_client: Optional[Any] = None
) -> List[ConversionResult]:
    """
    便捷函数：运行课程转换管道
    
    Args:
        raw_courses_dir: 原始课程目录
        markdown_courses_dir: 输出课程目录（转换后的 markdown）
        llm_client: 可选的LLM客户端
    
    Returns:
        转换结果列表
    """
    pipeline = CoursePipeline(
        raw_courses_dir=raw_courses_dir,
        markdown_courses_dir=markdown_courses_dir,
        llm_client=llm_client
    )
    return pipeline.convert_all()
