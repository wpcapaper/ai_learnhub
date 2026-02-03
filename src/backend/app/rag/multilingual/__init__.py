"""多语言支持模块（Extra功能）"""

from .detector import detect_language, LanguageDetector
from .query_expander import QueryExpander

__all__ = ["detect_language", "LanguageDetector", "QueryExpander"]
