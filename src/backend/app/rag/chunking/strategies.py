"""文档切割策略"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .metadata import Chunk, extract_metadata, generate_chunk_id


class ChunkingStrategy(ABC):
    """切割策略抽象基类"""
    
    @abstractmethod
    def chunk(
        self,
        content: str,
        code: str,
        source_file: str,
        kb_version: int = 1,
        **kwargs
    ) -> List[Chunk]:
        """
        切割文档
        
        Args:
            content: 文档内容（Markdown格式）
            code: 课程代码（目录名）
            source_file: 源文件路径（相对于课程目录）
            kb_version: 知识库版本号
        
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
        code: str,
        source_file: str,
        kb_version: int = 1,
        **kwargs
    ) -> List[Chunk]:
        """按语义边界切割，保持标题与内容的关联"""
        chunks = []
        
        # 按Markdown标题层级分割成sections
        sections = self._split_by_headers(content)
        
        position = 0
        for section in sections:
            section_text = section["text"].strip()
            if not section_text:
                continue
            
            # 计算section在原文中的字符位置
            char_start = section.get("char_start", 0)
            char_end = section.get("char_end", char_start + len(section_text))
            
            # 如果section太大，需要进一步切割
            if len(section_text) > self.max_chunk_size:
                sub_chunks = self._split_large_section(
                    section_text,
                    code,
                    source_file,
                    kb_version,
                    position,
                    char_start,
                    section.get("header_level", 0)
                )
                chunks.extend(sub_chunks)
                position += len(sub_chunks)
            else:
                chunk_id = generate_chunk_id(code, source_file, position)
                chunk = Chunk(
                    chunk_id=chunk_id,
                    text=section_text,
                    metadata=extract_metadata(
                        section_text,
                        code,
                        source_file,
                        position,
                        char_start,
                        char_end,
                        section.get("type", "paragraph"),
                        kb_version
                    )
                )
                chunks.append(chunk)
                position += 1
        
        return chunks
    
    def _split_by_headers(self, content: str) -> List[Dict[str, Any]]:
        """
        按Markdown标题分割，保持标题与后续内容的关联
        
        每个section包含标题及其下的所有内容（直到下一个同级或更高级标题）
        同时记录字符位置信息
        """
        sections = []
        lines = content.split('\n')
        
        current_section = {
            "text": "",
            "type": "paragraph",
            "header_level": 0,
            "has_code": False,
            "char_start": 0
        }
        in_code_block = False
        in_table = False
        char_pos = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            line_len = len(line) + 1  # +1 for newline
            
            # 代码块处理（不解析内部内容）
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                current_section["has_code"] = True
                current_section["text"] += line + "\n"
                char_pos += line_len
                continue
            
            if in_code_block:
                current_section["text"] += line + "\n"
                char_pos += line_len
                continue
            
            # 表格处理
            if '|' in stripped and stripped.startswith('|'):
                in_table = True
                current_section["text"] += line + "\n"
                char_pos += line_len
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
                        current_section["char_end"] = char_pos
                        sections.append(current_section)
                    
                    current_section = {
                        "text": line + "\n",
                        "type": "heading",
                        "header_level": header_level,
                        "has_code": False,
                        "char_start": char_pos
                    }
                else:
                    # 子标题，追加到当前section
                    current_section["text"] += line + "\n"
                
                char_pos += line_len
                continue
            
            # 普通内容追加到当前section
            current_section["text"] += line + "\n"
            char_pos += line_len
        
        # 添加最后一个section
        if current_section["text"].strip():
            current_section["type"] = "code_block" if current_section["has_code"] else "paragraph"
            current_section["char_end"] = char_pos
            sections.append(current_section)
        
        return sections
    
    def _split_large_section(
        self,
        text: str,
        code: str,
        source_file: str,
        kb_version: int,
        base_position: int,
        base_char_start: int,
        header_level: int = 0
    ) -> List[Chunk]:
        """
        切割过大的section，优先保持代码块和表格的完整性
        
        Args:
            text: 需要切割的文本
            code: 课程代码
            source_file: 源文件路径
            kb_version: 知识库版本号
            base_position: 基础位置序号
            base_char_start: 基础字符起始位置
            header_level: 标题层级
        """
        chunks = []
        
        # 先尝试按子结构分割
        sub_sections = self._split_preserve_blocks(text)
        
        position = 0
        current_chunk_text = ""
        current_char_start = base_char_start
        char_offset = 0
        
        for sub in sub_sections:
            sub_text = sub["text"].strip()
            sub_type = sub.get("type", "paragraph")
            sub_char_start = base_char_start + char_offset
            sub_char_end = sub_char_start + len(sub_text)
            
            # 代码块和表格完全不拆分，保持完整性
            if sub_type in ("code_block", "table"):
                if current_chunk_text:
                    chunk_id = generate_chunk_id(code, source_file, base_position + position)
                    chunk = Chunk(
                        chunk_id=chunk_id,
                        text=current_chunk_text.strip(),
                        metadata=extract_metadata(
                            current_chunk_text,
                            code,
                            source_file,
                            base_position + position,
                            current_char_start,
                            base_char_start + char_offset - 1,
                            "paragraph",
                            kb_version
                        )
                    )
                    chunks.append(chunk)
                    position += 1
                    current_chunk_text = ""
                
                # 完整保留代码块/表格，即使超过 max_chunk_size
                chunk_id = generate_chunk_id(code, source_file, base_position + position)
                chunk = Chunk(
                    chunk_id=chunk_id,
                    text=sub_text,
                    metadata=extract_metadata(
                        sub_text,
                        code,
                        source_file,
                        base_position + position,
                        sub_char_start,
                        sub_char_end,
                        sub_type,
                        kb_version
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
                        chunk_id = generate_chunk_id(code, source_file, base_position + position)
                        chunk = Chunk(
                            chunk_id=chunk_id,
                            text=current_chunk_text.strip(),
                            metadata=extract_metadata(
                                current_chunk_text,
                                code,
                                source_file,
                                base_position + position,
                                current_char_start,
                                base_char_start + char_offset - 1,
                                "paragraph",
                                kb_version
                            )
                        )
                        chunks.append(chunk)
                        position += 1
                        current_char_start = base_char_start + char_offset
                    
                    current_chunk_text = sub_text
            
            char_offset += len(sub.get("raw_text", sub_text)) + 2  # +2 for paragraph break
        
        # 添加最后的chunk
        if current_chunk_text.strip():
            chunk_id = generate_chunk_id(code, source_file, base_position + position)
            chunk = Chunk(
                chunk_id=chunk_id,
                text=current_chunk_text.strip(),
                metadata=extract_metadata(
                    current_chunk_text,
                    code,
                    source_file,
                    base_position + position,
                    current_char_start,
                    base_char_start + char_offset - 1,
                    "paragraph",
                    kb_version
                )
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_preserve_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        分割文本但保持代码块和表格的完整性
        同时将代码块前的简短说明文字与代码块合并
        返回每个子块的字符位置信息
        """
        sections = []
        lines = text.split('\n')
        
        current = {"text": "", "type": "paragraph", "raw_text": ""}
        in_code = False
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            raw_line = line + "\n"
            
            # 代码块开始
            if stripped.startswith('```'):
                if not in_code:
                    # 代码块开始：检查前面是否有简短说明（小于200字符）
                    preceding_text = current["text"].strip()
                    if preceding_text and len(preceding_text) < 200:
                        # 简短说明，合并到代码块
                        current["text"] = preceding_text + "\n" + line + "\n"
                        current["raw_text"] += raw_line
                        current["type"] = "code_block"
                    else:
                        # 较长说明，单独成段
                        if preceding_text:
                            sections.append(current)
                        current = {"text": line + "\n", "type": "code_block", "raw_text": raw_line}
                    in_code = True
                else:
                    # 代码块结束
                    current["text"] += line + "\n"
                    current["raw_text"] += raw_line
                    sections.append(current)
                    current = {"text": "", "type": "paragraph", "raw_text": ""}
                    in_code = False
                continue
            
            if in_code:
                current["text"] += line + "\n"
                current["raw_text"] += raw_line
                continue
            
            # 表格检测
            is_table_row = stripped.startswith('|') and '|' in stripped[1:]
            if is_table_row:
                if not in_table:
                    if current["text"].strip():
                        sections.append(current)
                    current = {"text": line + "\n", "type": "table", "raw_text": raw_line}
                    in_table = True
                else:
                    current["text"] += line + "\n"
                    current["raw_text"] += raw_line
                continue
            elif in_table:
                # 表格结束
                sections.append(current)
                current = {"text": line + "\n", "type": "paragraph", "raw_text": raw_line}
                in_table = False
                continue
            
            current["text"] += line + "\n"
            current["raw_text"] += raw_line
        
        if current["text"].strip():
            sections.append(current)
        
        return sections


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
        code: str,
        source_file: str,
        kb_version: int = 1,
        **kwargs
    ) -> List[Chunk]:
        """按固定大小切割"""
        chunks = []
        text = content.strip()
        
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
                chunk_id = generate_chunk_id(code, source_file, position)
                chunk = Chunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata=extract_metadata(
                        chunk_text,
                        code,
                        source_file,
                        position,
                        start,
                        end,
                        "paragraph",
                        kb_version
                    )
                )
                chunks.append(chunk)
                position += 1
            
            # 移动到下一个位置（考虑重叠）
            start = end - self.overlap_size
            if start < 0:
                start = end
        
        return chunks
