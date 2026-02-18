"""查询扩展模块（Extra功能）"""

from typing import List, Optional
import re

from .detector import detect_language


class QueryExpander:
    """查询扩展器 - 通过同义词、重写等方式扩展查询"""
    
    # 简单的中文同义词词典（示例）
    CHINESE_SYNONYMS = {
        "学习": ["学习", "掌握", "了解", "理解"],
        "问题": ["问题", "疑问", "困惑"],
        "解释": ["解释", "说明", "阐述"],
    }
    
    def __init__(self, use_llm: bool = False, llm_client=None):
        """
        Args:
            use_llm: 是否使用LLM进行查询重写
            llm_client: LLM客户端（如果使用）
        """
        self.use_llm = use_llm
        self.llm_client = llm_client
    
    def expand(self, query: str, max_variants: int = 3) -> List[str]:
        """
        扩展查询
        
        Args:
            query: 原始查询
            max_variants: 最大变体数量
        
        Returns:
            扩展后的查询列表（包含原始查询）
        """
        expanded = [query]
        
        # 同义词扩展
        synonyms = self._get_synonyms(query)
        expanded.extend(synonyms[:max_variants - 1])
        
        # LLM重写（如果启用）
        if self.use_llm and self.llm_client:
            rewritten = self._rewrite_with_llm(query, max_variants - len(expanded))
            expanded.extend(rewritten)
        
        return expanded[:max_variants]
    
    def _get_synonyms(self, query: str) -> List[str]:
        """获取同义词扩展"""
        lang = detect_language(query)
        
        if lang.startswith("zh"):
            return self._get_chinese_synonyms(query)
        else:
            return []
    
    def _get_chinese_synonyms(self, query: str) -> List[str]:
        """获取中文同义词"""
        variants = []
        
        for word, synonyms in self.CHINESE_SYNONYMS.items():
            if word in query:
                for synonym in synonyms:
                    if synonym != word:
                        variant = query.replace(word, synonym)
                        if variant != query:
                            variants.append(variant)
        
        return variants
    
    def _rewrite_with_llm(self, query: str, max_count: int) -> List[str]:
        """使用LLM重写查询"""
        # TODO: 实现LLM查询重写
        # 示例prompt:
        # "请为以下问题生成3个不同但意思相近的表述：{query}"
        return []
