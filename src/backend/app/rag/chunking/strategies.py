"""文档切割策略"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import uuid

from .metadata import Chunk, extract_metadata


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
    """语义切割策略 - 按Markdown结构切割"""
    
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
        **kwargs
    ) -> List[Chunk]:
        """按语义边界切割"""
        chunks = []
        
        # 按Markdown结构分割
        sections = self._split_by_structure(content)
        
        position = 0
        for section in sections:
            section_text = section["text"].strip()
            if not section_text:
                continue
            
            # 如果段落太长，进一步切割
            if len(section_text) > self.max_chunk_size:
                sub_chunks = self._split_long_section(
                    section_text,
                    course_id,
                    chapter_id,
                    chapter_title,
                    position
                )
                chunks.extend(sub_chunks)
                position += len(sub_chunks)
            else:
                # 如果段落太短，尝试合并
                if len(section_text) < self.min_chunk_size and chunks:
                    # 合并到上一个chunk
                    last_chunk = chunks[-1]
                    merged_text = last_chunk.text + "\n\n" + section_text
                    if len(merged_text) <= self.max_chunk_size:
                        last_chunk.text = merged_text
                        continue
                
                # 创建新chunk
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=section_text,
                    metadata=extract_metadata(
                        section_text,
                        course_id,
                        chapter_id,
                        chapter_title,
                        position,
                        section.get("type", "paragraph")
                    )
                )
                chunks.append(chunk)
                position += 1
        
        return chunks
    
    def _split_by_structure(self, content: str) -> List[Dict[str, Any]]:
        """按Markdown结构分割"""
        sections = []
        
        # 按标题、代码块、列表等分割
        lines = content.split('\n')
        current_section = {"text": "", "type": "paragraph"}
        
        in_code_block = False
        code_block_lang = ""
        
        for line in lines:
            # 检测代码块
            if line.strip().startswith('```'):
                if in_code_block:
                    # 结束代码块
                    current_section["text"] += line + "\n"
                    sections.append(current_section)
                    current_section = {"text": "", "type": "paragraph"}
                    in_code_block = False
                else:
                    # 开始代码块
                    if current_section["text"].strip():
                        sections.append(current_section)
                    code_block_lang = line.strip()[3:].strip()
                    current_section = {
                        "text": line + "\n",
                        "type": f"code_{code_block_lang}" if code_block_lang else "code"
                    }
                    in_code_block = True
                continue
            
            if in_code_block:
                current_section["text"] += line + "\n"
                continue
            
            # 检测标题
            if line.strip().startswith('#'):
                if current_section["text"].strip():
                    sections.append(current_section)
                # 标题单独成段
                sections.append({
                    "text": line + "\n",
                    "type": "heading"
                })
                current_section = {"text": "", "type": "paragraph"}
                continue
            
            # 检测列表
            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                if current_section["type"] != "list":
                    if current_section["text"].strip():
                        sections.append(current_section)
                    current_section = {"text": line + "\n", "type": "list"}
                else:
                    current_section["text"] += line + "\n"
                continue
            
            # 空行分割段落
            if not line.strip():
                if current_section["text"].strip():
                    sections.append(current_section)
                    current_section = {"text": "", "type": "paragraph"}
                continue
            
            # 普通文本
            current_section["text"] += line + "\n"
        
        # 添加最后一个section
        if current_section["text"].strip():
            sections.append(current_section)
        
        return sections
    
    def _split_long_section(
        self,
        text: str,
        course_id: str,
        chapter_id: Optional[str],
        chapter_title: Optional[str],
        base_position: int
    ) -> List[Chunk]:
        """切割过长的段落"""
        chunks = []
        
        # 按句子分割
        sentences = re.split(r'([。！？\n])', text)
        current_chunk = ""
        position = 0
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
            
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk:
                    chunk = Chunk(
                        chunk_id=str(uuid.uuid4()),
                        text=current_chunk.strip(),
                        metadata=extract_metadata(
                            current_chunk,
                            course_id,
                            chapter_id,
                            chapter_title,
                            base_position + position,
                            "paragraph"
                        )
                    )
                    chunks.append(chunk)
                    position += 1
                
                # 重叠处理
                if chunks and self.overlap_size > 0:
                    overlap_text = current_chunk[-self.overlap_size:]
                    current_chunk = overlap_text + sentence
                else:
                    current_chunk = sentence
            else:
                current_chunk += sentence
        
        # 添加最后一个chunk
        if current_chunk.strip():
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                text=current_chunk.strip(),
                metadata=extract_metadata(
                    current_chunk,
                    course_id,
                    chapter_id,
                    chapter_title,
                    base_position + position,
                    "paragraph"
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
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    metadata=extract_metadata(
                        chunk_text,
                        course_id,
                        chapter_id,
                        chapter_title,
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
