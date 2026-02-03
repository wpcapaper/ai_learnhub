"""Chunk元数据定义"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid


@dataclass
class Chunk:
    """文档片段"""
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[list] = None
    
    def __post_init__(self):
        """初始化chunk_id"""
        if not self.chunk_id:
            self.chunk_id = str(uuid.uuid4())


def extract_metadata(
    text: str,
    course_id: str,
    chapter_id: Optional[str] = None,
    chapter_title: Optional[str] = None,
    position: int = 0,
    content_type: str = "paragraph"
) -> Dict[str, Any]:
    """
    提取chunk元数据
    
    Args:
        text: 文本内容
        course_id: 课程ID
        chapter_id: 章节ID
        chapter_title: 章节标题
        position: 在文档中的位置
        content_type: 内容类型（paragraph, code, list, table等）
    
    Returns:
        元数据字典
    """
    return {
        "course_id": course_id,
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "position": position,
        "content_type": content_type,
        "text_length": len(text),
        "word_count": len(text.split()),
    }
