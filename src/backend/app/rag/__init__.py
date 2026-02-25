"""
RAG (Retrieval-Augmented Generation) 模块

为助学Agent提供课程内容检索功能
"""

from .service import RAGService
from .retrieval.tool import retrieve_course_content, retrieve_course_chunks, retrieve_chapter_chunks, build_rag_context

__all__ = [
    "RAGService",
    "retrieve_course_content",
    "retrieve_course_chunks",
    "retrieve_chapter_chunks",
    "build_rag_context",
]
