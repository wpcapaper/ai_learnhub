"""语言检测模块"""

from typing import Optional
try:
    from langdetect import detect, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    
    # 设置种子以确保结果一致性
    DetectorFactory.seed = 0
    
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


def detect_language(text: str) -> str:
    """
    检测文本语言
    
    Args:
        text: 文本内容
    
    Returns:
        语言代码（如 'zh-cn', 'en'）
    """
    if not LANGDETECT_AVAILABLE:
        # 简单启发式检测
        return _simple_language_detect(text)
    
    try:
        lang = detect(text)
        # 标准化语言代码
        lang_map = {
            "zh": "zh-cn",
            "zh-cn": "zh-cn",
            "zh-tw": "zh-tw",
        }
        return lang_map.get(lang, lang)
    except LangDetectException:
        return _simple_language_detect(text)


def _simple_language_detect(text: str) -> str:
    """简单的语言检测（基于字符）"""
    # 中文字符范围
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len([c for c in text if c.isalnum() or '\u4e00' <= c <= '\u9fff'])
    
    if total_chars == 0:
        return "unknown"
    
    chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
    
    if chinese_ratio > 0.3:
        return "zh-cn"
    else:
        return "en"


class LanguageDetector:
    """语言检测器"""
    
    def detect(self, text: str) -> str:
        """检测语言"""
        return detect_language(text)
    
    def is_chinese(self, text: str) -> bool:
        """判断是否为中文"""
        lang = self.detect(text)
        return lang.startswith("zh")
    
    def is_english(self, text: str) -> bool:
        """判断是否为英文"""
        lang = self.detect(text)
        return lang == "en"
