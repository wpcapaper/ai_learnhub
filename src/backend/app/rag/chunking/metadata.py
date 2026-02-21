"""Chunk元数据定义"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from .version import CURRENT_STRATEGY_VERSION


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
    source_file: Optional[str] = None,
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
        source_file: 源文件路径（用于跨设备复用）
        position: 在文档中的位置
        content_type: 内容类型（paragraph, code, list, table等）
    
    Returns:
        元数据字典，包含版本控制和token估算信息
    """
    char_count = len(text)
    
    # 估算 token 数
    # 中文约 1.5 字符/token，英文约 4 字符/token，混合取中间值约 2
    estimated_tokens = int(char_count / 2)
    
    # 根据 token 数判断大小级别
    if estimated_tokens < 512:
        token_level = "normal"
    elif estimated_tokens < 1024:
        token_level = "warning"
    elif estimated_tokens < 2048:
        token_level = "large"
    else:
        token_level = "oversized"
    
    return {
        "course_id": course_id,
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "source_file": source_file or chapter_title,
        "position": position,
        "content_type": content_type,
        "char_count": char_count,
        "word_count": len(text.split()),
        "estimated_tokens": estimated_tokens,
        "token_level": token_level,
        # 版本控制字段
        "strategy_version": CURRENT_STRATEGY_VERSION,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }
