"""内容过滤器 - 识别哪些内容适合做embedding"""

import re
from typing import List, Tuple


class ContentFilter:
    """内容过滤器"""
    
    # 代码块标记
    CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```', re.MULTILINE)
    
    # 纯代码行（无注释）
    CODE_LINE_PATTERN = re.compile(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[=\(\)\[\]{}:;,]', re.MULTILINE)
    
    # 数学公式（LaTeX）
    FORMULA_PATTERN = re.compile(r'\$[\s\S]*?\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)')
    
    # 图片标记
    IMAGE_PATTERN = re.compile(r'!\[.*?\]\(.*?\)')
    
    # 导航/目录标记
    NAVIGATION_PATTERNS = [
        re.compile(r'^#{1,6}\s*(目录|Contents|Table of Contents)', re.IGNORECASE),
        re.compile(r'^\[.*?\]\(#.*?\)', re.MULTILINE),  # 锚点链接
    ]
    
    @classmethod
    def should_embed(cls, text: str, content_type: str = "paragraph") -> bool:
        """
        判断内容是否适合做embedding
        
        Args:
            text: 文本内容
            content_type: 内容类型
        
        Returns:
            True表示适合做embedding，False表示不适合
        """
        # 空内容或过短内容
        text_stripped = text.strip()
        if len(text_stripped) < 10:
            return False
        
        # 纯代码块（无注释说明）
        if cls._is_pure_code(text_stripped):
            return False
        
        # 纯公式
        if cls._is_pure_formula(text_stripped):
            return False
        
        # 图片标记
        if cls._is_image_only(text_stripped):
            return False
        
        # 导航/目录
        if cls._is_navigation(text_stripped):
            return False
        
        return True
    
    @classmethod
    def _is_pure_code(cls, text: str) -> bool:
        """判断是否为纯代码（无注释）"""
        # 移除代码块标记
        text_no_blocks = cls.CODE_BLOCK_PATTERN.sub('', text)
        
        # 如果移除代码块后内容很少，说明主要是代码
        if len(text_no_blocks.strip()) < len(text) * 0.2:
            # 检查是否有注释
            has_comment = bool(re.search(r'#|//|/\*|\*/\s*[^\s]', text))
            if not has_comment:
                return True
        
        return False
    
    @classmethod
    def _is_pure_formula(cls, text: str) -> bool:
        """判断是否为纯公式"""
        # 移除公式后的文本
        text_no_formula = cls.FORMULA_PATTERN.sub('', text).strip()
        # 如果移除公式后内容很少，说明主要是公式
        return len(text_no_formula) < len(text) * 0.3
    
    @classmethod
    def _is_image_only(cls, text: str) -> bool:
        """判断是否仅为图片标记"""
        text_no_image = cls.IMAGE_PATTERN.sub('', text).strip()
        return len(text_no_image) < 10
    
    @classmethod
    def _is_navigation(cls, text: str) -> bool:
        """判断是否为导航/目录"""
        for pattern in cls.NAVIGATION_PATTERNS:
            if pattern.search(text):
                return True
        return False
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        清理文本，移除不适合embedding的部分
        
        Args:
            text: 原始文本
        
        Returns:
            清理后的文本
        """
        # 移除纯代码块（保留有注释的）
        # 这里简单处理，实际可以更复杂
        cleaned = text
        
        # 移除图片标记
        cleaned = cls.IMAGE_PATTERN.sub('', cleaned)
        
        return cleaned.strip()


def filter_chunks(chunks: List[Tuple[str, dict]]) -> List[Tuple[str, dict]]:
    """
    过滤chunks，只保留适合embedding的
    
    Args:
        chunks: (text, metadata) 列表
    
    Returns:
        过滤后的chunks
    """
    filtered = []
    for text, metadata in chunks:
        content_type = metadata.get("content_type", "paragraph")
        if ContentFilter.should_embed(text, content_type):
            # 清理文本
            cleaned_text = ContentFilter.clean_text(text)
            if cleaned_text:
                filtered.append((cleaned_text, metadata))
    
    return filtered
