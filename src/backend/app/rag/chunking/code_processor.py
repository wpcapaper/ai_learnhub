"""
代码块处理器

处理Markdown中的代码块，支持三种策略：
- preserve: 保留原样
- summarize: 使用LLM生成摘要
- hybrid: 长代码生成摘要，短代码保留原样
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessedCodeBlock:
    """处理后的代码块"""
    content: str                    # 处理后的内容（可能是摘要或原代码）
    original_code: Optional[str]    # 原始代码（如果content是摘要）
    content_type: str               # 'code' 或 'summary'
    language: str                   # 代码语言
    char_count: int                 # 原始字符数


# LLM摘要提示词模板
CODE_SUMMARY_PROMPT = """你是一位技术文档专家。请为以下代码生成简洁的摘要，用于语义检索。

要求：
1. 摘要长度控制在 100-200 字
2. 说明代码的主要功能和用途
3. 提及关键函数/类名
4. 使用中文

代码语言: {language}

```{language}
{code}
```

请直接输出摘要，不要有任何前缀或额外说明。"""


class CodeBlockProcessor:
    """
    代码块处理器
    
    根据配置的策略处理代码块：
    - preserve: 保留原样，适合短代码
    - summarize: 使用LLM生成摘要，适合长代码
    - hybrid: 混合策略，根据长度阈值决定
    """
    
    def __init__(
        self,
        strategy: str = "hybrid",
        summary_threshold: int = 500,
        llm_client=None
    ):
        """
        初始化代码块处理器
        
        Args:
            strategy: 处理策略（preserve/summarize/hybrid）
            summary_threshold: 触发摘要的字符数阈值
            llm_client: LLM客户端实例（summarize策略需要）
        """
        self.strategy = strategy
        self.summary_threshold = summary_threshold
        self._llm_client = llm_client
    
    def _get_llm_client(self):
        """延迟获取LLM客户端"""
        if self._llm_client is None:
            from app.llm import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client
    
    def process(
        self,
        code: str,
        language: str = ""
    ) -> ProcessedCodeBlock:
        """
        处理单个代码块
        
        Args:
            code: 代码内容
            language: 代码语言
        
        Returns:
            ProcessedCodeBlock 处理后的代码块
        """
        char_count = len(code)
        
        # 根据策略决定处理方式
        if self.strategy == "preserve":
            return self._preserve(code, language, char_count)
        
        elif self.strategy == "summarize":
            return self._summarize(code, language, char_count)
        
        elif self.strategy == "hybrid":
            # 混合策略：短代码保留，长代码生成摘要
            if char_count < self.summary_threshold:
                return self._preserve(code, language, char_count)
            else:
                return self._summarize(code, language, char_count)
        
        else:
            # 未知策略，默认保留
            logger.warning(f"未知的代码块处理策略: {self.strategy}，使用保留策略")
            return self._preserve(code, language, char_count)
    
    def _preserve(
        self,
        code: str,
        language: str,
        char_count: int
    ) -> ProcessedCodeBlock:
        """保留原样策略"""
        return ProcessedCodeBlock(
            content=code,
            original_code=None,
            content_type="code",
            language=language,
            char_count=char_count
        )
    
    def _summarize(
        self,
        code: str,
        language: str,
        char_count: int
    ) -> ProcessedCodeBlock:
        """生成摘要策略"""
        try:
            llm = self._get_llm_client()
            
            prompt = CODE_SUMMARY_PROMPT.format(
                language=language or "unknown",
                code=code
            )
            
            # 使用同步接口（适合后台任务）
            response = llm.chat_sync(
                messages=[
                    {"role": "system", "content": "你是技术文档专家，擅长总结代码功能。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.content.strip()
            
            logger.debug(f"代码块摘要生成成功，原长度: {char_count}，摘要长度: {len(summary)}")
            
            return ProcessedCodeBlock(
                content=summary,
                original_code=code,
                content_type="summary",
                language=language,
                char_count=char_count
            )
            
        except Exception as e:
            # 摘要失败时降级为保留原样
            logger.warning(f"代码块摘要生成失败: {e}，降级为保留原样")
            return self._preserve(code, language, char_count)
    
    async def process_async(
        self,
        code: str,
        language: str = ""
    ) -> ProcessedCodeBlock:
        """
        异步处理单个代码块
        
        Args:
            code: 代码内容
            language: 代码语言
        
        Returns:
            ProcessedCodeBlock 处理后的代码块
        """
        char_count = len(code)
        
        if self.strategy == "preserve":
            return self._preserve(code, language, char_count)
        
        elif self.strategy == "summarize":
            return await self._summarize_async(code, language, char_count)
        
        elif self.strategy == "hybrid":
            if char_count < self.summary_threshold:
                return self._preserve(code, language, char_count)
            else:
                return await self._summarize_async(code, language, char_count)
        
        else:
            return self._preserve(code, language, char_count)
    
    async def _summarize_async(
        self,
        code: str,
        language: str,
        char_count: int
    ) -> ProcessedCodeBlock:
        """异步生成摘要"""
        try:
            llm = self._get_llm_client()
            
            prompt = CODE_SUMMARY_PROMPT.format(
                language=language or "unknown",
                code=code
            )
            
            response = await llm.chat(
                messages=[
                    {"role": "system", "content": "你是技术文档专家，擅长总结代码功能。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.content.strip()
            
            return ProcessedCodeBlock(
                content=summary,
                original_code=code,
                content_type="summary",
                language=language,
                char_count=char_count
            )
            
        except Exception as e:
            logger.warning(f"代码块摘要生成失败: {e}，降级为保留原样")
            return self._preserve(code, language, char_count)
