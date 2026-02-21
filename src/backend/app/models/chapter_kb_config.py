"""
章节知识库配置模型
用于存储每个章节的RAG配置（切分策略、检索模式等）

设计要点：
1. 以 Chapter 为维度，而非整个 Course
2. 支持元数据回填（导入前生成embedding的情况）
3. 预留 GraphRAG 相关字段
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, Float, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class ChapterKBConfig(Base):
    """章节知识库配置模型
    
    存储每个章节的 RAG 配置，包括：
    - 切分策略配置
    - 代码块处理策略
    - 检索配置
    - GraphRAG 预留字段
    - 索引状态
    """
    
    __tablename__ = "chapter_kb_configs"
    
    # ==================== 主键与关联 ====================
    id = Column(String(36), primary_key=True, index=True)
    
    # 章节ID（可为空，用于导入前生成embedding的场景）
    chapter_id = Column(String(36), ForeignKey('chapters.id'), nullable=True, index=True)
    
    # 课程ID（可为空，用于导入前生成embedding的场景）
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=True, index=True)
    
    # 临时标识符（导入前使用，如文件路径，用于匹配回填）
    temp_ref = Column(String(255), nullable=True, index=True)
    
    # ==================== 切分策略配置 ====================
    # 切分策略类型：semantic（语义切分）/ fixed（固定大小）/ heading（按标题）
    chunking_strategy = Column(String(20), default='semantic', nullable=False)
    
    # 最大块大小（字符数）
    chunk_size = Column(Integer, default=1000, nullable=False)
    
    # 块重叠大小（字符数）
    chunk_overlap = Column(Integer, default=200, nullable=False)
    
    # 最小块大小（字符数）
    min_chunk_size = Column(Integer, default=100, nullable=False)
    
    # ==================== 代码块处理配置 ====================
    # 代码块处理策略：preserve（保留原样）/ summarize（LLM摘要）/ hybrid（混合）
    code_block_strategy = Column(String(20), default='hybrid', nullable=False)
    
    # 触发摘要的代码块长度阈值（字符数）
    code_summary_threshold = Column(Integer, default=500, nullable=False)
    
    # ==================== 检索配置 ====================
    # 检索模式：vector（纯向量）/ hybrid（混合检索）/ vector_rerank（向量+重排序）/ graph（图检索）
    retrieval_mode = Column(String(20), default='vector', nullable=False)
    
    # 默认返回数量
    default_top_k = Column(Integer, default=5, nullable=False)
    
    # 相似度阈值
    score_threshold = Column(Float, default=0.0, nullable=False)
    
    # ==================== GraphRAG 预留字段 ====================
    # 是否启用知识图谱提取
    enable_graph_extraction = Column(Boolean, default=False, nullable=False)
    
    # 实体类型配置 JSON 数组，如 ["概念", "方法", "工具"]
    graph_entity_types = Column(JSON, nullable=True)
    
    # 关系类型配置 JSON 数组，如 ["包含", "依赖", "等价"]
    graph_relation_types = Column(JSON, nullable=True)
    
    # ==================== 索引状态 ====================
    # 最后索引时间
    indexed_at = Column(DateTime, nullable=True)
    
    # 文档块数量
    chunk_count = Column(Integer, default=0, nullable=False)
    
    # 知识图谱实体数量（GraphRAG）
    graph_entity_count = Column(Integer, default=0, nullable=False)
    
    # 知识图谱关系数量（GraphRAG）
    graph_relation_count = Column(Integer, default=0, nullable=False)
    
    # 索引状态：not_indexed / indexing / indexed / failed
    index_status = Column(String(20), default='not_indexed', nullable=False)
    
    # 索引错误信息（失败时记录）
    index_error = Column(Text, nullable=True)
    
    # 当前进行中的任务ID（用于追踪任务进度）
    current_task_id = Column(String(50), nullable=True)
    
    # ==================== 元数据回填状态 ====================
    # course_id/chapter_id 是否已回填
    metadata_backfilled = Column(Boolean, default=False, nullable=False)
    
    # ==================== 元数据 ====================
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    
    # ==================== 关系 ====================
    chapter = relationship("Chapter", backref="kb_config")
    course = relationship("Course", backref="kb_configs")
    
    # ==================== 约束 ====================
    __table_args__ = (
        # chapter_id 或 temp_ref 必须有值
        CheckConstraint('chapter_id IS NOT NULL OR temp_ref IS NOT NULL', name='chk_kb_config_ref'),
    )
    
    def __repr__(self):
        return f"<ChapterKBConfig(id='{self.id}' chapter_id='{self.chapter_id}' status='{self.index_status}')>"
    
    def to_dict(self):
        """转换为字典（用于API响应）"""
        return {
            "id": self.id,
            "chapter_id": self.chapter_id,
            "course_id": self.course_id,
            "temp_ref": self.temp_ref,
            "chunking_strategy": self.chunking_strategy,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "min_chunk_size": self.min_chunk_size,
            "code_block_strategy": self.code_block_strategy,
            "code_summary_threshold": self.code_summary_threshold,
            "retrieval_mode": self.retrieval_mode,
            "default_top_k": self.default_top_k,
            "score_threshold": self.score_threshold,
            "enable_graph_extraction": self.enable_graph_extraction,
            "graph_entity_types": self.graph_entity_types,
            "graph_relation_types": self.graph_relation_types,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "chunk_count": self.chunk_count,
            "graph_entity_count": self.graph_entity_count,
            "graph_relation_count": self.graph_relation_count,
            "index_status": self.index_status,
            "index_error": self.index_error,
            "current_task_id": self.current_task_id,
            "metadata_backfilled": self.metadata_backfilled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
