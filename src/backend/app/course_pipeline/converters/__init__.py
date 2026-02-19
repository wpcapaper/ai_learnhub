"""
课程转换管道 - 核心转换器模块

该模块提供各种格式课程的转换器：
- IPynbConverter: 将 Jupyter Notebook 转换为 Markdown
- MarkdownConverter: 处理和优化 Markdown 文件
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import re

from ..models import (
    Chapter,
    SourceFile,
    ContentType,
)


class BaseConverter(ABC):
    """转换器抽象基类"""
    
    @abstractmethod
    def convert(self, source_file: SourceFile, output_dir: Path) -> List[Chapter]:
        """
        将源文件转换为章节列表
        
        Args:
            source_file: 源文件信息
            output_dir: 输出目录路径
        
        Returns:
            转换后的章节列表
        """
        pass
    
    @abstractmethod
    def supports(self, content_type: ContentType) -> bool:
        """检查是否支持该内容类型"""
        pass


class IPynbConverter(BaseConverter):
    """
    Jupyter Notebook 转换器
    
    将 .ipynb 文件转换为 Markdown 格式，特殊处理代码单元格
    """
    
    def supports(self, content_type: ContentType) -> bool:
        return content_type == ContentType.IPYNB
    
    def convert(self, source_file: SourceFile, output_dir: Path) -> List[Chapter]:
        """
        转换 Jupyter Notebook 文件
        
        处理策略：
        1. Markdown单元格 → 直接转换为Markdown文本
        2. Code单元格 → 带语言标记的代码块，并添加执行说明
        3. 输出单元格 → 作为代码执行结果展示
        """
        chapters = []
        
        try:
            with open(source_file.path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)
        except Exception as e:
            print(f"读取 ipynb 文件失败: {source_file.path}, 错误: {e}")
            return chapters
        
        # 获取 notebook 元数据
        nb_metadata = notebook.get('metadata', {})
        language_info = nb_metadata.get('language_info', {})
        default_language = language_info.get('name', 'python')
        
        # 获取所有单元格
        cells = notebook.get('cells', [])
        
        # 按标题分割章节（如果notebook中有标题单元格）
        current_chapter_content = []
        current_chapter_title = self._extract_title(notebook) or "notebook 内容"
        chapter_start_idx = 0
        
        for idx, cell in enumerate(cells):
            cell_type = cell.get('cell_type', '')
            source = cell.get('source', [])
            
            # 确保 source 是字符串
            if isinstance(source, list):
                source_text = ''.join(source)
            else:
                source_text = source
            
            # 检查是否是标题单元格（Markdown中的#标题）
            if cell_type == 'markdown':
                heading_match = re.match(r'^#+\s+(.+)$', source_text.strip(), re.MULTILINE)
                if heading_match:
                    heading_text = heading_match.group(1).strip()
                    # 检查是否是一级标题（新章节）
                    if source_text.strip().startswith('# '):
                        # 保存之前的章节
                        if current_chapter_content:
                            chapter_content = '\n\n'.join(current_chapter_content)
                            chapters.append(Chapter(
                                title=current_chapter_title,
                                content=chapter_content,
                                file_name=self._generate_filename(current_chapter_title, chapter_start_idx),
                                sort_order=chapter_start_idx,
                                source_file=source_file.path,
                                word_count=len(chapter_content)
                            ))
                        
                        # 开始新章节
                        current_chapter_title = heading_text
                        current_chapter_content = [source_text]
                        chapter_start_idx = idx
                        continue
                
                current_chapter_content.append(source_text)
            
            elif cell_type == 'code':
                # 处理代码单元格
                code_block = self._format_code_cell(source_text, cell, default_language)
                current_chapter_content.append(code_block)
        
        # 添加最后一个章节
        if current_chapter_content:
            chapter_content = '\n\n'.join(current_chapter_content)
            chapters.append(Chapter(
                title=current_chapter_title,
                content=chapter_content,
                file_name=self._generate_filename(current_chapter_title, chapter_start_idx),
                sort_order=chapter_start_idx,
                source_file=source_file.path,
                word_count=len(chapter_content)
            ))
        
        # 如果没有分章节，将整个notebook作为一个章节
        if not chapters and cells:
            all_content = []
            for cell in cells:
                cell_type = cell.get('cell_type', '')
                source = cell.get('source', [])
                source_text = ''.join(source) if isinstance(source, list) else source
                
                if cell_type == 'markdown':
                    all_content.append(source_text)
                elif cell_type == 'code':
                    all_content.append(self._format_code_cell(source_text, cell, default_language))
            
            content = '\n\n'.join(all_content)
            chapters.append(Chapter(
                title=self._extract_title(notebook) or Path(source_file.path).stem,
                content=content,
                file_name=f"{Path(source_file.path).stem}.md",
                sort_order=0,
                source_file=source_file.path,
                word_count=len(content)
            ))
        
        return chapters
    
    def _extract_title(self, notebook: Dict[str, Any]) -> Optional[str]:
        """从 notebook 中提取标题"""
        # 尝试从第一个单元格提取标题
        cells = notebook.get('cells', [])
        for cell in cells:
            if cell.get('cell_type') == 'markdown':
                source = cell.get('source', [])
                source_text = ''.join(source) if isinstance(source, list) else source
                # 查找一级标题
                match = re.search(r'^#\s+(.+)$', source_text.strip(), re.MULTILINE)
                if match:
                    return match.group(1).strip()
        return None
    
    def _format_code_cell(self, code: str, cell: Dict[str, Any], language: str) -> str:
        """
        格式化代码单元格
        
        将代码和输出转换为带注释的Markdown格式
        """
        parts = []
        
        # 添加代码块
        if code.strip():
            # 清理代码中的魔法命令提示
            cleaned_code = self._clean_magic_commands(code)
            parts.append(f"```{language}\n{cleaned_code}\n```")
        
        # 添加输出（如果有）
        outputs = cell.get('outputs', [])
        if outputs:
            output_parts = []
            for output in outputs:
                output_type = output.get('output_type', '')
                
                if output_type == 'stream':
                    text = ''.join(output.get('text', []))
                    if text.strip():
                        output_parts.append(text)
                
                elif output_type == 'execute_result':
                    data = output.get('data', {})
                    # 优先使用文本输出
                    if 'text/plain' in data:
                        output_parts.append(data['text/plain'])
                    # 如果有图片，添加图片标记
                    elif 'image/png' in data:
                        output_parts.append("\n*[执行结果包含图片]*\n")
                
                elif output_type == 'error':
                    ename = output.get('ename', 'Error')
                    evalue = output.get('evalue', '')
                    output_parts.append(f"```\n{ename}: {evalue}\n```")
            
            if output_parts:
                output_text = '\n'.join(output_parts)
                parts.append(f"\n**执行结果：**\n\n{output_text}")
        
        return '\n'.join(parts)
    
    def _clean_magic_commands(self, code: str) -> str:
        """清理 Jupyter 魔法命令，添加注释说明"""
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 处理常见的魔法命令
            if line.strip().startswith('%%'):
                # 单元格魔法命令，添加说明
                cleaned_lines.append(f"# [Notebook魔法命令: {line.strip()}]")
            elif line.strip().startswith('!'):
                # Shell 命令
                cleaned_lines.append(f"# [Shell命令] {line.strip()[1:]}")
            elif line.strip().startswith('%'):
                # 行魔法命令
                cleaned_lines.append(f"# [魔法命令] {line.strip()}")
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _generate_filename(self, title: str, index: int) -> str:
        """生成章节文件名"""
        # 清理标题中的特殊字符
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', title)
        safe_title = re.sub(r'\s+', '_', safe_title.strip())
        
        # 添加序号前缀
        return f"{index:02d}_{safe_title[:50]}.md"


class MarkdownConverter(BaseConverter):
    """
    Markdown 转换器
    
    处理和优化 Markdown 文件，支持章节拆分和格式规范化
    """
    
    def supports(self, content_type: ContentType) -> bool:
        return content_type == ContentType.MARKDOWN
    
    def convert(self, source_file: SourceFile, output_dir: Path) -> List[Chapter]:
        """
        转换 Markdown 文件
        
        处理策略：
        1. 按一级标题分割章节
        2. 规范化标题层级
        3. 清理格式问题
        """
        chapters = []
        
        try:
            with open(source_file.path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取 Markdown 文件失败: {source_file.path}, 错误: {e}")
            return chapters
        
        # 按一级标题分割
        sections = self._split_by_h1(content)
        
        for idx, (title, section_content) in enumerate(sections):
            # 规范化内容
            normalized_content = self._normalize_content(section_content)
            
            # 生成文件名
            file_name = self._generate_filename(title, idx, source_file.path)
            
            chapters.append(Chapter(
                title=title,
                content=normalized_content,
                file_name=file_name,
                sort_order=idx,
                source_file=source_file.path,
                word_count=len(normalized_content)
            ))
        
        # 如果没有一级标题，整个文件作为一个章节
        if not chapters and content.strip():
            file_name = Path(source_file.path).stem
            chapters.append(Chapter(
                title=file_name,
                content=self._normalize_content(content),
                file_name=f"{file_name}.md",
                sort_order=0,
                source_file=source_file.path,
                word_count=len(content)
            ))
        
        return chapters
    
    def _split_by_h1(self, content: str) -> List[tuple]:
        """按一级标题分割内容"""
        sections = []
        lines = content.split('\n')
        
        current_title = "前言"
        current_content = []
        
        for line in lines:
            if line.startswith('# '):
                # 保存之前的章节
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                
                # 开始新章节
                current_title = line[2:].strip()
                current_content = [line]
            else:
                current_content.append(line)
        
        # 添加最后一个章节
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))
        
        return sections
    
    def _normalize_content(self, content: str) -> str:
        """规范化 Markdown 内容"""
        # 移除多余的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 确保代码块前后有空行
        content = re.sub(r'([^\n])\n```', r'\1\n\n```', content)
        content = re.sub(r'```\n([^\n])', r'```\n\n\1', content)
        
        # 规范化列表格式
        content = re.sub(r'^(\s*[-*+])  +', r'\1 ', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def _generate_filename(self, title: str, index: int, source_path: str) -> str:
        """生成章节文件名"""
        # 如果源文件有序号前缀，保留它
        source_name = Path(source_path).stem
        match = re.match(r'^(\d+)[_-]?(.+)$', source_name)
        if match and index == 0:
            prefix = match.group(1)
            # 清理标题
            safe_title = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', title)
            safe_title = re.sub(r'\s+', '_', safe_title.strip())
            return f"{prefix}_{safe_title[:50]}.md"
        
        # 否则使用序号
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', title)
        safe_title = re.sub(r'\s+', '_', safe_title.strip())
        return f"{index:02d}_{safe_title[:50]}.md"


class ConverterRegistry:
    """转换器注册表"""
    
    def __init__(self):
        self._converters: List[BaseConverter] = []
        self._register_default_converters()
    
    def _register_default_converters(self):
        """注册默认转换器"""
        self.register(IPynbConverter())
        self.register(MarkdownConverter())
    
    def register(self, converter: BaseConverter):
        """注册转换器"""
        self._converters.append(converter)
    
    def get_converter(self, content_type: ContentType) -> Optional[BaseConverter]:
        """获取支持指定内容类型的转换器"""
        for converter in self._converters:
            if converter.supports(content_type):
                return converter
        return None
