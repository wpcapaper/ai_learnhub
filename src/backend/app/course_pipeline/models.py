"""
课程转换管道数据模型

定义课程转换过程中使用的所有数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class IssueType(Enum):
    """质量问题的类型枚举"""
    CONTROVERSIAL = "controversial"      # 争议性内容
    ERROR = "error"                      # 明显错误
    OUTDATED = "outdated"               # 过时信息
    INCOMPLETE = "incomplete"           # 内容不完整
    SUGGESTION = "suggestion"           # 改进建议
    QUESTION = "question"               # 存疑待确认


class IssueSeverity(Enum):
    """问题严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentType(Enum):
    """内容类型枚举"""
    MARKDOWN = "markdown"
    IPYNB = "ipynb"
    PDF = "pdf"
    DOCX = "docx"


@dataclass
class SourceFile:
    """源文件信息"""
    path: str                           # 文件绝对路径
    content_type: ContentType           # 内容类型
    size: int = 0                       # 文件大小（字节）
    modified_time: Optional[datetime] = None  # 修改时间
    relative_path: str = ""             # 相对于课程目录的路径（不含文件名）
    
    @classmethod
    def from_path(cls, path: str, course_dir: Optional[str] = None) -> "SourceFile":
        """从文件路径创建源文件信息"""
        import os
        from pathlib import Path
        
        file_path = Path(path)
        ext = file_path.suffix.lower()
        content_type_map = {
            ".md": ContentType.MARKDOWN,
            ".ipynb": ContentType.IPYNB,
            ".pdf": ContentType.PDF,
            ".docx": ContentType.DOCX,
        }
        content_type = content_type_map.get(ext, ContentType.MARKDOWN)
        
        try:
            stat = os.stat(path)
            size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime)
        except:
            size = 0
            modified_time = None
        
        relative_path = ""
        if course_dir:
            try:
                rel = file_path.relative_to(course_dir)
                if len(rel.parts) > 1:
                    relative_path = str(Path(*rel.parts[:-1]))
            except ValueError:
                pass
        
        return cls(
            path=path,
            content_type=content_type,
            size=size,
            modified_time=modified_time,
            relative_path=relative_path
        )


@dataclass
class RawCourse:
    """原始课程数据结构"""
    course_id: str                              # 课程唯一标识
    name: str                                   # 课程名称
    source_dir: str                             # 源目录路径
    description: str = ""                       # 课程描述
    source_files: List[SourceFile] = field(default_factory=list)  # 源文件列表
    metadata: Dict[str, Any] = field(default_factory=dict)        # 额外元数据
    
    def get_files_by_type(self, content_type: ContentType) -> List[SourceFile]:
        """按类型获取源文件"""
        return [f for f in self.source_files if f.content_type == content_type]


@dataclass
class Chapter:
    """章节信息"""
    title: str                                  # 章节标题
    content: str                                # 章节内容（Markdown格式）
    file_name: str                              # 输出文件名
    code: str = ""                              # 章节唯一标识（课程内），如 "introduction"
    sort_order: int = 0                         # 排序序号
    source_file: Optional[str] = None           # 来源文件
    source_section: Optional[str] = None        # 来源章节（如ipynb中的某个section）
    word_count: int = 0                         # 字数统计
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """计算字数"""
        if self.content and self.word_count == 0:
            # 简单的中文字数统计
            self.word_count = len(self.content.replace('\n', '').replace(' ', ''))


@dataclass
class QualityIssue:
    """质量问题记录"""
    issue_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    issue_type: IssueType = IssueType.SUGGESTION
    severity: IssueSeverity = IssueSeverity.LOW
    
    # 位置信息
    file_name: str = ""                         # 文件名
    line_start: Optional[int] = None            # 起始行号
    line_end: Optional[int] = None              # 结束行号
    text_snippet: str = ""                      # 相关文本片段
    
    # 问题描述
    title: str = ""                             # 问题标题
    description: str = ""                       # 详细描述
    suggestion: str = ""                        # 修改建议
    references: List[str] = field(default_factory=list)  # 参考资料
    
    # 状态管理
    status: str = "pending"                     # pending | confirmed | fixed | ignored | false_positive
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None


@dataclass
class QualityReport:
    """课程质量评估报告"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str = ""
    
    # 总体评分 (0-100)
    overall_score: int = 0
    completeness_score: int = 0      # 完整性评分
    consistency_score: int = 0       # 一致性评分
    accuracy_score: int = 0          # 准确性评分
    
    # 问题统计
    issues: List[QualityIssue] = field(default_factory=list)
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    
    # 报告内容
    summary: str = ""                          # 总结
    recommendations: List[str] = field(default_factory=list)  # 整体建议
    
    # 元数据
    evaluated_at: datetime = field(default_factory=datetime.now)
    evaluator_version: str = "1.0.0"
    
    def add_issue(self, issue: QualityIssue):
        """添加问题并更新统计"""
        self.issues.append(issue)
        self.total_issues += 1
        
        if issue.severity == IssueSeverity.CRITICAL:
            self.critical_issues += 1
        elif issue.severity == IssueSeverity.HIGH:
            self.high_issues += 1
        elif issue.severity == IssueSeverity.MEDIUM:
            self.medium_issues += 1
        else:
            self.low_issues += 1
    
    def calculate_overall_score(self):
        """根据问题统计计算总分"""
        # 基础分100，按问题严重程度扣分
        deduction = (
            self.critical_issues * 25 +
            self.high_issues * 10 +
            self.medium_issues * 3 +
            self.low_issues * 1
        )
        self.overall_score = max(0, 100 - deduction)
        
        # 如果没有问题，设置高分
        if self.total_issues == 0:
            self.overall_score = 95


@dataclass
class ConvertedCourse:
    """转换后的课程数据结构"""
    course_id: str                              # 课程唯一标识
    code: str                                   # 课程代码（用于URL和标识）
    title: str                                  # 课程标题
    description: str = ""                       # 课程描述
    cover_image: str = ""                       # 封面图片URL
    chapters: List[Chapter] = field(default_factory=list)  # 章节列表
    quality_report: Optional[QualityReport] = None  # 质量报告
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def _generate_chapter_code(self, chapter: Chapter) -> str:
        """为章节生成唯一标识
        
        优先级：
        1. 已有的 chapter.code
        2. 从 file_name 提取（去掉序号前缀和扩展名）
        """
        if chapter.code:
            return chapter.code
        
        import re
        # 从 file_name 提取，如 "01_introduction.md" -> "introduction"
        name = chapter.file_name
        
        # 去掉扩展名
        if '.' in name:
            name = name.rsplit('.', 1)[0]
        
        # 去掉序号前缀（如 01_, 1-, 1.）
        name = re.sub(r'^\d+[._-]', '', name)
        name = re.sub(r'^\d+$', '', name)  # 纯数字的情况
        
        # 转为小写，替换空格和特殊字符
        code = name.lower().replace(' ', '_').replace('-', '_')
        code = re.sub(r'[^a-z0-9_\u4e00-\u9fff]', '', code)
        
        return code or f"chapter_{chapter.sort_order}"
    
    def to_course_json(self) -> Dict[str, Any]:
        """转换为 course.json 格式"""
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "cover_image": self.cover_image,
            "chapters": [
                {
                    "code": self._generate_chapter_code(ch),
                    "title": ch.title,
                    "file": ch.file_name,
                    "sort_order": ch.sort_order
                }
                for ch in sorted(self.chapters, key=lambda x: x.sort_order)
            ]
        }


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool                               # 是否成功
    course: Optional[ConvertedCourse] = None    # 转换后的课程
    error_message: str = ""                     # 错误信息
    warnings: List[str] = field(default_factory=list)  # 警告信息
    processing_time: float = 0.0                # 处理耗时（秒）
