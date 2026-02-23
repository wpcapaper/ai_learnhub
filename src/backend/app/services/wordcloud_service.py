"""
词云生成服务

使用 jieba TF-IDF 算法提取课程/章节文本中的关键词，
生成词云数据（JSON格式），存储在课程目录下。

设计说明：
- 不依赖 matplotlib，只生成词频数据
- 前端使用 react-wordcloud 渲染
- 词云文件存储在课程目录，检测到即视为有词云

存储结构：
    raw_courses/{课程名}/
    ├── wordcloud.json           # 课程级词云（聚合所有章节）
    └── chapters/
        └── {章节名}/
            └── wordcloud.json   # 章节级词云
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# jieba 分词和关键词提取
import jieba
import jieba.analyse


@dataclass
class WordcloudData:
    """词云数据结构"""
    version: str = "1.0"
    generated_at: str = ""
    words: List[Dict[str, float]] = None  # [{"word": "关键词", "weight": 0.95}, ...]
    source_stats: Dict = None  # {"total_chars": 10000, "unique_words": 500, "top_words_count": 50}
    
    def __post_init__(self):
        if self.words is None:
            self.words = []
        if self.source_stats is None:
            self.source_stats = {}
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "words": self.words,
            "source_stats": self.source_stats
        }


class WordcloudService:
    """
    词云生成服务
    
    核心功能：
    1. 使用 jieba TF-IDF 提取关键词及权重
    2. 生成课程级词云（聚合所有章节内容）
    3. 生成章节级词云（单个 markdown 文件）
    4. 词云数据的读取、删除、状态检查
    """
    
    # 默认配置
    DEFAULT_TOP_K = 50  # 默认提取的关键词数量
    DEFAULT_COURSES_DIR = "raw_courses"  # 默认课程目录
    
    # 停用词列表（可扩展）
    STOPWORDS = {
        # 中文停用词
        "的", "是", "在", "和", "了", "有", "不", "这", "我", "他", "她",
        "它", "们", "你", "您", "就", "也", "都", "会", "说", "要", "好",
        "能", "可以", "一个", "这个", "那个", "什么", "怎么", "如何", "为什么",
        # 英文停用词
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "can", "this", "that", "these", "those",
        "i", "you", "he", "she", "it", "we", "they", "what", "which", "who",
        "when", "where", "why", "how", "all", "each", "every", "both", "few",
        "more", "most", "other", "some", "such", "no", "not", "only", "same",
        "so", "than", "too", "very", "just", "but", "and", "or", "if", "then",
        # 代码相关停用词
        "code", "example", "file", "path", "true", "false", "null", "none",
        "return", "def", "class", "import", "from", "self", "init",
        # 标点符号（jieba 通常会过滤，但保险起见）
        "，", "。", "！", "？", "；", "：", """, """, "'", "'",
        "（", "）", "【", "】", "《", "》", "、", "…",
    }
    
    def __init__(self, courses_dir: str = None):
        """
        初始化词云服务
        
        Args:
            courses_dir: 课程目录路径，默认为 raw_courses
        """
        self.courses_dir = Path(courses_dir or self.DEFAULT_COURSES_DIR)
        
        # 初始化 jieba（加载停用词）
        self._init_jieba()
    
    def _init_jieba(self):
        """
        初始化 jieba 分词器
        
        设置停用词，提高关键词提取质量
        """
        # 添加自定义停用词到 jieba
        for word in self.STOPWORDS:
            jieba.add_word(word, freq=0, tag='stopword')
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本内容
        
        移除 markdown 语法、代码块等，保留有意义的文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的纯文本
        """
        # 移除代码块（包括语言标识）
        text = re.sub(r'```[\s\S]*?```', '', text)
        
        # 移除行内代码
        text = re.sub(r'`[^`]+`', '', text)
        
        # 移除 markdown 链接，保留链接文本
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # 移除 markdown 图片
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        
        # 移除 markdown 标题符号
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        
        # 移除 markdown 列表符号
        text = re.sub(r'^[\*\-\+]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
        
        # 移除 markdown 表格分隔符
        text = re.sub(r'\|[-:]+\|', '', text)
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除 URL
        text = re.sub(r'https?://\S+', '', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _filter_keywords(self, keywords: List[Tuple[str, float]]) -> List[Dict[str, float]]:
        """
        过滤关键词
        
        移除停用词、纯数字、单字符等无意义词
        
        Args:
            keywords: jieba 提取的关键词列表 [(word, weight), ...]
            
        Returns:
            过滤后的关键词列表 [{"word": word, "weight": weight}, ...]
        """
        filtered = []
        
        for word, weight in keywords:
            # 跳过停用词
            if word.lower() in self.STOPWORDS or word in self.STOPWORDS:
                continue
            
            # 跳过纯数字
            if word.isdigit():
                continue
            
            # 跳过单字符（除非是常见英文缩写）
            if len(word) == 1 and not word.isalpha():
                continue
            
            # 跳过纯标点符号
            if not re.search(r'[\u4e00-\u9fa5a-zA-Z0-9]', word):
                continue
            
            # 归一化权重到 0-1 范围
            normalized_weight = round(weight, 4)
            
            filtered.append({
                "word": word,
                "weight": normalized_weight
            })
        
        return filtered
    
    def extract_keywords(self, text: str, top_k: int = None) -> List[Dict[str, float]]:
        """
        使用 jieba TF-IDF 提取关键词
        
        Args:
            text: 待提取的文本内容
            top_k: 提取的关键词数量，默认使用 DEFAULT_TOP_K
            
        Returns:
            关键词列表 [{"word": "关键词", "weight": 0.95}, ...]
        """
        top_k = top_k or self.DEFAULT_TOP_K
        
        # 清理文本
        cleaned_text = self._clean_text(text)
        
        # 如果清理后文本过短，直接返回空列表
        if len(cleaned_text) < 100:
            return []
        
        # 使用 jieba TF-IDF 提取关键词
        keywords = jieba.analyse.extract_tags(
            cleaned_text,
            topK=top_k,
            withWeight=True
        )
        
        # 过滤关键词
        filtered_keywords = self._filter_keywords(keywords)
        
        return filtered_keywords
    
    def generate_course_wordcloud(
        self, 
        course_path: Path, 
        top_k: int = None
    ) -> Dict:
        """
        生成课程级词云（聚合所有章节内容）
        
        Args:
            course_path: 课程目录路径
            top_k: 提取的关键词数量
            
        Returns:
            词云数据字典
        """
        if not course_path.exists():
            raise FileNotFoundError(f"课程目录不存在: {course_path}")
        
        # 收集所有 markdown 文件内容
        all_text = []
        md_files = list(course_path.glob("**/*.md"))
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                all_text.append(content)
            except Exception as e:
                print(f"警告: 读取文件失败 {md_file}: {e}")
                continue
        
        if not all_text:
            raise ValueError(f"课程目录中没有找到有效的 markdown 文件: {course_path}")
        
        # 合并所有文本
        combined_text = "\n".join(all_text)
        
        # 提取关键词
        words = self.extract_keywords(combined_text, top_k)
        
        # 计算统计信息
        source_stats = {
            "total_chars": len(combined_text),
            "total_files": len(md_files),
            "unique_words": len(set(combined_text.split())),
            "top_words_count": len(words)
        }
        
        # 构建词云数据
        wordcloud_data = WordcloudData(
            generated_at=datetime.now().isoformat(),
            words=words,
            source_stats=source_stats
        )
        
        # 保存到课程目录
        output_path = course_path / "wordcloud.json"
        output_path.write_text(
            json.dumps(wordcloud_data.to_dict(), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        return wordcloud_data.to_dict()
    
    def generate_chapter_wordcloud(
        self,
        chapter_path: Path,
        top_k: int = None
    ) -> Dict:
        """
        生成章节级词云
        
        Args:
            chapter_path: 章节 markdown 文件路径
            top_k: 提取的关键词数量
            
        Returns:
            词云数据字典
        """
        if not chapter_path.exists():
            raise FileNotFoundError(f"章节文件不存在: {chapter_path}")
        
        if not chapter_path.suffix == '.md':
            raise ValueError(f"章节文件必须是 markdown 格式: {chapter_path}")
        
        # 读取章节内容
        content = chapter_path.read_text(encoding='utf-8')
        
        # 提取关键词
        words = self.extract_keywords(content, top_k)
        
        # 计算统计信息
        source_stats = {
            "total_chars": len(content),
            "unique_words": len(set(content.split())),
            "top_words_count": len(words)
        }
        
        # 构建词云数据
        wordcloud_data = WordcloudData(
            generated_at=datetime.now().isoformat(),
            words=words,
            source_stats=source_stats
        )
        
        # 保存到章节目录
        # 存储路径: {课程目录}/chapters/{章节名}/wordcloud.json
        chapter_name = chapter_path.stem  # 获取文件名（不含扩展名）
        output_dir = chapter_path.parent / "chapters" / chapter_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / "wordcloud.json"
        output_path.write_text(
            json.dumps(wordcloud_data.to_dict(), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        return wordcloud_data.to_dict()
    
    def get_course_wordcloud(self, course_path: Path) -> Optional[Dict]:
        """
        读取课程级词云数据
        
        Args:
            course_path: 课程目录路径
            
        Returns:
            词云数据字典，如果不存在则返回 None
        """
        wordcloud_path = course_path / "wordcloud.json"
        
        if not wordcloud_path.exists():
            return None
        
        try:
            content = wordcloud_path.read_text(encoding='utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"警告: 读取词云文件失败 {wordcloud_path}: {e}")
            return None
    
    def get_chapter_wordcloud(
        self, 
        course_path: Path, 
        chapter_name: str
    ) -> Optional[Dict]:
        """
        读取章节级词云数据
        
        Args:
            course_path: 课程目录路径
            chapter_name: 章节名称（markdown 文件名，不含扩展名）
            
        Returns:
            词云数据字典，如果不存在则返回 None
        """
        wordcloud_path = course_path / "chapters" / chapter_name / "wordcloud.json"
        
        if not wordcloud_path.exists():
            return None
        
        try:
            content = wordcloud_path.read_text(encoding='utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"警告: 读取章节词云文件失败 {wordcloud_path}: {e}")
            return None
    
    def has_course_wordcloud(self, course_path: Path) -> bool:
        """
        检查课程是否存在词云
        
        Args:
            course_path: 课程目录路径
            
        Returns:
            是否存在课程词云
        """
        return (course_path / "wordcloud.json").exists()
    
    def has_chapter_wordcloud(self, course_path: Path, chapter_name: str) -> bool:
        """
        检查章节是否存在词云
        
        Args:
            course_path: 课程目录路径
            chapter_name: 章节名称
            
        Returns:
            是否存在章节词云
        """
        return (course_path / "chapters" / chapter_name / "wordcloud.json").exists()
    
    def delete_course_wordcloud(self, course_path: Path) -> bool:
        """
        删除课程级词云
        
        Args:
            course_path: 课程目录路径
            
        Returns:
            是否删除成功
        """
        wordcloud_path = course_path / "wordcloud.json"
        
        if wordcloud_path.exists():
            wordcloud_path.unlink()
            return True
        
        return False
    
    def delete_chapter_wordcloud(
        self, 
        course_path: Path, 
        chapter_name: str
    ) -> bool:
        """
        删除章节级词云
        
        Args:
            course_path: 课程目录路径
            chapter_name: 章节名称
            
        Returns:
            是否删除成功
        """
        wordcloud_path = course_path / "chapters" / chapter_name / "wordcloud.json"
        
        if wordcloud_path.exists():
            wordcloud_path.unlink()
            # 尝试删除空目录
            try:
                wordcloud_path.parent.rmdir()
            except:
                pass
            return True
        
        return False
    
    def batch_generate_wordclouds(
        self, 
        course_path: Path,
        top_k: int = None
    ) -> Dict:
        """
        批量生成课程和所有章节的词云
        
        Args:
            course_path: 课程目录路径
            top_k: 提取的关键词数量
            
        Returns:
            包含课程词云和所有章节词云的结果
        """
        result = {
            "course": None,
            "chapters": [],
            "errors": []
        }
        
        # 生成课程词云
        try:
            result["course"] = self.generate_course_wordcloud(course_path, top_k)
        except Exception as e:
            result["errors"].append(f"课程词云生成失败: {str(e)}")
        
        # 生成所有章节词云
        for md_file in course_path.glob("**/*.md"):
            # 跳过 assets 目录下的文件
            if "assets" in str(md_file).lower():
                continue
            
            try:
                chapter_wordcloud = self.generate_chapter_wordcloud(md_file, top_k)
                result["chapters"].append({
                    "chapter": md_file.stem,
                    "path": str(md_file.relative_to(course_path)),
                    "wordcloud": chapter_wordcloud
                })
            except Exception as e:
                result["errors"].append(f"章节 {md_file.stem} 词云生成失败: {str(e)}")
        
        return result
    
    def list_chapter_wordclouds(self, course_path: Path) -> List[Dict]:
        """
        列出课程下所有章节的词云状态
        
        从 course.json 获取章节信息（包含 sort_order），
        确保返回的数据与课程配置一致。
        
        Args:
            course_path: 课程目录路径
            
        Returns:
            章节词云状态列表，按 sort_order 排序
        """
        import json
        chapters = []
        
        # 从 course.json 读取章节信息
        course_json_path = course_path / "course.json"
        if course_json_path.exists():
            try:
                with open(course_json_path, 'r', encoding='utf-8') as f:
                    course_json = json.load(f)
                
                for ch in course_json.get("chapters", []):
                    file_path = ch.get("file", "")
                    chapter_name = Path(file_path).stem if file_path else ""
                    sort_order = ch.get("sort_order", 0)
                    
                    has_wordcloud = self.has_chapter_wordcloud(course_path, chapter_name) if chapter_name else False
                    
                    chapters.append({
                        "name": chapter_name,
                        "title": ch.get("title", chapter_name),
                        "path": file_path,
                        "sort_order": sort_order,
                        "has_wordcloud": has_wordcloud
                    })
                
                # 按 sort_order 排序
                chapters.sort(key=lambda x: x.get("sort_order", 0))
                return chapters
            except (json.JSONDecodeError, IOError):
                pass
        
        # 回退：遍历 markdown 文件（兼容没有 course.json 的情况）
        for md_file in course_path.glob("**/*.md"):
            if "assets" in str(md_file).lower():
                continue
            
            chapter_name = md_file.stem
            has_wordcloud = self.has_chapter_wordcloud(course_path, chapter_name)
            
            chapters.append({
                "name": chapter_name,
                "title": chapter_name,
                "path": str(md_file.relative_to(course_path)),
                "sort_order": 999,  # 未知顺序放最后
                "has_wordcloud": has_wordcloud
            })
        
        return chapters
