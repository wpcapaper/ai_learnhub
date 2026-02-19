"""
课程转换管道模块

该模块负责将 raw_courses 目录下的原始课程文件转换为系统可接受的标准格式，
并存储在 courses 目录中。

主要功能：
1. 支持 ipynb 和 markdown 格式的课程文件转换
2. 自动编排章节顺序
3. 课程质量评估
4. RAG 分块与索引准备
"""

from .models import (
    RawCourse,
    ConvertedCourse,
    Chapter,
    QualityReport,
    QualityIssue,
    ConversionResult,
)
from .pipeline import CoursePipeline

__all__ = [
    "RawCourse",
    "ConvertedCourse", 
    "Chapter",
    "QualityReport",
    "QualityIssue",
    "ConversionResult",
    "CoursePipeline",
]
