"""
Chunk元数据定义

按照 RAG_ARCHITECTURE.md 规范设计的元数据结构：
- code: 课程代码（目录名）
- source_file: 相对于课程目录的文件路径
- position: chunk在文件中的序号
- char_start/char_end: 原文中的字符位置（精准定位）
- content_type: 内容类型
- char_count: 字符数
- estimated_tokens: 估算token数
- kb_version: 知识库版本号
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import hashlib


def generate_chunk_id(code: str, source_file: str, position: int) -> str:
    """
    生成稳定的 chunk ID
    
    格式: {code}__{file_hash}__{position:04d}
    示例: python_basics__a1b2c3d4__0005
    
    设计理由：
    - 基于内容位置而非随机 UUID，支持幂等索引
    - 同一文件重新索引，相同位置的 chunk ID 不变
    - 便于调试和问题定位
    
    Args:
        code: 课程代码（目录名）
        source_file: 源文件路径
        position: chunk在文件中的序号（0-based）
    
    Returns:
        稳定的 chunk ID 字符串
    """
    file_hash = hashlib.md5(source_file.encode()).hexdigest()[:8]
    return f"{code}__{file_hash}__{position:04d}"


@dataclass
class Chunk:
    """文档片段"""
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[list] = None
    
    def __post_init__(self):
        """初始化后验证"""
        if not self.chunk_id:
            raise ValueError("chunk_id 不能为空")


def extract_metadata(
    text: str,
    code: str,
    source_file: str,
    position: int,
    char_start: int,
    char_end: int,
    content_type: str = "paragraph",
    kb_version: int = 1
) -> Dict[str, Any]:
    """
    提取 chunk 元数据
    
    按照 RAG_ARCHITECTURE.md 规范，Metadata 包含以下字段：
    - code: 课程代码（目录名）
    - source_file: 相对于课程目录的文件路径
    - position: chunk 在文件中的序号（0-based）
    - char_start: 原文起始字符位置
    - char_end: 原文结束字符位置
    - content_type: 内容类型（paragraph/code/table/heading/list）
    - char_count: 字符数
    - estimated_tokens: 估算 token 数
    - kb_version: 知识库版本号
    
    Args:
        text: 文本内容
        code: 课程代码（目录名）
        source_file: 源文件路径（相对于课程目录）
        position: chunk 在文件中的序号（0-based）
        char_start: 原文起始字符位置
        char_end: 原文结束字符位置
        content_type: 内容类型
        kb_version: 知识库版本号
    
    Returns:
        元数据字典
    """
    char_count = len(text)
    
    # 估算 token 数
    # 中文约 1.5 字符/token，英文约 4 字符/token，混合取中间值约 2
    estimated_tokens = int(char_count / 2)
    
    return {
        # === 核心标识（必填）===
        "code": code,                    # 课程代码（目录名）
        "source_file": source_file,      # 相对于课程目录的文件路径
        "position": position,            # chunk 在文件中的序号（0-based）
        
        # === 精准定位（知识图谱追溯需要）===
        "char_start": char_start,        # 原文起始字符位置
        "char_end": char_end,            # 原文结束字符位置
        
        # === 内容类型 ===
        "content_type": content_type,    # paragraph/code/table/heading/list
        
        # === 统计字段（用于管理展示）===
        "char_count": char_count,        # 字符数
        "estimated_tokens": estimated_tokens,  # 估算 token 数
        
        # === 版本管理 ===
        "kb_version": kb_version,        # 当前 Collection 的版本号
    }
