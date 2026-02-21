"""文档切割策略"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import uuid

from .metadata import Chunk, extract_metadata
from .version import CHUNK_STRATEGY_VERSION, CURRENT_STRATEGY_VERSION


class ChunkingStrategy(ABC):
    """切割策略抽象基类"""
    
    @abstractmethod
    def chunk(
        self,
        content: str,
        course_id: str,
        chapter_id: Optional[str] = None,
        chapter_title: Optional[str] = None,
        **kwargs
    ) -> List[Chunk]:
        """
        切割文档
        
        Args:
            content: 文档内容（Markdown格式）
            course_id: 课程ID
            chapter_id: 章节ID
            chapter_title: 章节标题
            **kwargs: 其他参数
        
        Returns:
            Chunk列表
        """
        pass


class SemanticChunkingStrategy(ChunkingStrategy):
    """语义切割策略 - 按Markdown结构切割，保持标题与内容的关联"""
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        overlap_size: int = 200
    ):
        """
        Args:
            min_chunk_size: 最小chunk大小（字符数）
            max_chunk_size: 最大chunk大小（字符数）
            overlap_size: 重叠大小（字符数）
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
    
    def chunk(
        self,
        content: str,
        course_id: str,
        chapter_id: Optional[str] = None,
        chapter_title: Optional[str] = None,
        source_file: Optional[str] = None,
        **kwargs
    ) -> List[Chunk]:
        """按语义边界切割，保持标题与内容的关联"""
        chunks = []
        
        source = source_file or chapter_title or chapter_id
        
        # 按Markdown标题层级分割成sections
        sections = self._split_by_headers(content)
        
        position = 0
        for section in sections:
            section_text = section["text"].strip()
            if not section_text:
                continue
            
            # 如果section太大，需要进一步切割
            if len(section_text) > self.max_chunk_size:
                sub_chunks = self._split_large_section(
                    section_text,
                    course_id,
                    chapter_id,
                    chapter_title,
                    source,
                    position,
                    section.get("header_level", 0)
                )
                chunks.extend(sub_chunks)
                position += len(sub_chunks)
            else:
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=section_text,
                    metadata=extract_metadata(
                        section_text,
                        course_id,
                        chapter_id,
                        chapter_title,
                        source,
                        position,
                        section.get("type", "paragraph")
                    )
                )
                chunks.append(chunk)
                position += 1
        
        return chunks
    
    def _split_by_headers(self, content: str) -> List[Dict[str, Any]]:
        """
        按Markdown标题分割，保持标题与后续内容的关联
        
        每个section包含标题及其下的所有内容（直到下一个同级或更高级标题）
        """
        sections = []
        lines = content.split('\n')
        
        current_section = {"text": "", "type": "paragraph", "header_level": 0, "has_code": False}
        in_code_block = False
        in_table = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 代码块处理（不解析内部内容）
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                current_section["has_code"] = True
                current_section["text"] += line + "\n"
                continue
            
            if in_code_block:
                current_section["text"] += line + "\n"
                continue
            
            # 表格处理
            if '|' in stripped and stripped.startswith('|'):
                in_table = True
                current_section["text"] += line + "\n"
                continue
            elif in_table and not stripped.startswith('|'):
                in_table = False
            
            # 检测标题
            header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if header_match:
                header_level = len(header_match.group(1))
                
                # 如果是顶级标题（#）或与当前section同级或更高级，开始新section
                if header_level <= current_section.get("header_level", 0) or current_section.get("header_level", 0) == 0:
                    if current_section["text"].strip():
                        current_section["type"] = "code_block" if current_section["has_code"] else "paragraph"
                        sections.append(current_section)
                    current_section = {
                        "text": line + "\n",
                        "type": "heading",
                        "header_level": header_level,
                        "has_code": False
                    }
                else:
                    # 子标题，追加到当前section
                    current_section["text"] += line + "\n"
                continue
            
            # 普通内容追加到当前section
            current_section["text"] += line + "\n"
        
        # 添加最后一个section
        if current_section["text"].strip():
            current_section["type"] = "code_block" if current_section["has_code"] else "paragraph"
            sections.append(current_section)
        
        return sections
    
    def _split_large_section(
        self,
        text: str,
        course_id: str,
        chapter_id: Optional[str],
        chapter_title: Optional[str],
        source_file: Optional[str],
        base_position: int,
        header_level: int = 0
    ) -> List[Chunk]:
        """
        切割过大的section，优先保持代码块和表格的完整性
        """
        chunks = []
        
        # 先尝试按子结构分割
        sub_sections = self._split_preserve_blocks(text)
        
        position = 0
        current_chunk_text = ""
        
        for sub in sub_sections:
            sub_text = sub["text"].strip()
            sub_type = sub.get("type", "paragraph")
            
            # 代码块和表格完全不拆分，保持完整性
            if sub_type in ("code_block", "table"):
                if current_chunk_text:
                    chunk = Chunk(
                        chunk_id=str(uuid.uuid4()),
                        text=current_chunk_text.strip(),
                        metadata=extract_metadata(
                            current_chunk_text,
                            course_id,
                            chapter_id,
                            chapter_title,
                            source_file,
                            base_position + position,
                            "paragraph"
                        )
                    )
                    chunks.append(chunk)
                    position += 1
                    current_chunk_text = ""
                
                # 完整保留代码块/表格，即使超过 max_chunk_size
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=sub_text,
                    metadata=extract_metadata(
                        sub_text,
                        course_id,
                        chapter_id,
                        chapter_title,
                        source_file,
                        base_position + position,
                        sub_type
                    )
                )
                chunks.append(chunk)
                position += 1
            else:
                # 普通文本
                if len(current_chunk_text) + len(sub_text) + 2 <= self.max_chunk_size:
                    current_chunk_text += "\n\n" + sub_text if current_chunk_text else sub_text
                else:
                    if current_chunk_text:
                        chunk = Chunk(
                            chunk_id=str(uuid.uuid4()),
                            text=current_chunk_text.strip(),
                            metadata=extract_metadata(
                                current_chunk_text,
                                course_id,
                                chapter_id,
                                chapter_title,
                                source_file,
                                base_position + position,
                                "paragraph"
                            )
                        )
                        chunks.append(chunk)
                        position += 1
                    current_chunk_text = sub_text
        
        # 添加最后的chunk
        if current_chunk_text.strip():
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                text=current_chunk_text.strip(),
                metadata=extract_metadata(
                    current_chunk_text,
                    course_id,
                    chapter_id,
                    chapter_title,
                    source_file,
                    base_position + position,
                    "paragraph"
                )
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_preserve_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        分割文本但保持代码块和表格的完整性
        同时将代码块前的简短说明文字与代码块合并
        """
        sections = []
        lines = text.split('\n')
        
        current = {"text": "", "type": "paragraph"}
        in_code = False
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            
            # 代码块开始
            if stripped.startswith('```'):
                if not in_code:
                    # 代码块开始：检查前面是否有简短说明（小于200字符）
                    preceding_text = current["text"].strip()
                    if preceding_text and len(preceding_text) < 200:
                        # 简短说明，合并到代码块
                        current["text"] = preceding_text + "\n" + line + "\n"
                        current["type"] = "code_block"
                    else:
                        # 较长说明，单独成段
                        if preceding_text:
                            sections.append(current)
                        current = {"text": line + "\n", "type": "code_block"}
                    in_code = True
                else:
                    # 代码块结束
                    current["text"] += line + "\n"
                    sections.append(current)
                    current = {"text": "", "type": "paragraph"}
                    in_code = False
                continue
            
            if in_code:
                current["text"] += line + "\n"
                continue
            
            # 表格检测
            is_table_row = stripped.startswith('|') and '|' in stripped[1:]
            if is_table_row:
                if not in_table:
                    if current["text"].strip():
                        sections.append(current)
                    current = {"text": line + "\n", "type": "table"}
                    in_table = True
                else:
                    current["text"] += line + "\n"
                continue
            elif in_table:
                # 表格结束
                sections.append(current)
                current = {"text": line + "\n", "type": "paragraph"}
                in_table = False
                continue
            
            current["text"] += line + "\n"
        
        if current["text"].strip():
            sections.append(current)
        
        return sections
    
    def _split_code_by_lines(
        self,
        code_text: str,
        course_id: str,
        chapter_id: Optional[str],
        chapter_title: Optional[str],
        source_file: Optional[str],
        base_position: int,
        content_type: str
    ) -> List[Chunk]:
        """按行拆分过大的代码块"""
        chunks = []
        lines = code_text.split('\n')
        
        current = ""
        position = 0
        
        for line in lines:
            if len(current) + len(line) + 1 > self.max_chunk_size - 100:
                if current.strip():
                    chunk = Chunk(
                        chunk_id=str(uuid.uuid4()),
                        text=current.strip(),
                        metadata=extract_metadata(
                            current,
                            course_id,
                            chapter_id,
                            chapter_title,
                            source_file,
                            base_position + position,
                            content_type
                        )
                    )
                    chunks.append(chunk)
                    position += 1
                current = line + "\n"
            else:
                current += line + "\n"
        
        if current.strip():
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                text=current.strip(),
                metadata=extract_metadata(
                    current,
                    course_id,
                    chapter_id,
                    chapter_title,
                    source_file,
                    base_position + position,
                    content_type
                )
            )
            chunks.append(chunk)
        
        return chunks


class FixedSizeChunkingStrategy(ChunkingStrategy):
    """固定大小切割策略"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        overlap_size: int = 50
    ):
        """
        Args:
            chunk_size: chunk大小（字符数）
            overlap_size: 重叠大小（字符数）
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
    
    def chunk(
        self,
        content: str,
        course_id: str,
        chapter_id: Optional[str] = None,
        chapter_title: Optional[str] = None,
        source_file: Optional[str] = None,
        **kwargs
    ) -> List[Chunk]:
        """按固定大小切割"""
        chunks = []
        text = content.strip()
        
        source = source_file or chapter_title or chapter_id
        
        position = 0
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 尝试在句子边界切割
            if end < len(text):
                # 向后查找句号、换行等
                for i in range(end, min(end + 100, len(text))):
                    if text[i] in '。！？\n':
                        end = i + 1
                        break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    metadata=extract_metadata(
                        chunk_text,
                        course_id,
                        chapter_id,
                        chapter_title,
                        source,
                        position,
                        "paragraph"
                    )
                )
                chunks.append(chunk)
                position += 1
            
            # 移动到下一个位置（考虑重叠）
            start = end - self.overlap_size
            if start < 0:
                start = end
        
        return chunks
