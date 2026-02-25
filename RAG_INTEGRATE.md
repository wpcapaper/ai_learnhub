# RAG 接入说明

本文档面向提示词开发者，说明如何使用 RAG 工具函数获取召回结果并拼入提示词模板。

## 适用场景
- 课程级召回：跨章节检索，适合课程概览与跨章节问题。
- 章节级召回：限制在当前章节，避免跨章节误答。

## 工具函数
模块：`app.rag.retrieval.tool`

### 1) 课程级召回
```python
from app.rag.retrieval.tool import retrieve_course_chunks, build_rag_context

chunks = await retrieve_course_chunks(
    query="变量是什么",
    course_code="python_basics",
    top_k=5,
    score_threshold=0.0,
)

context = build_rag_context(chunks, max_context_chars=3000)
```

### 2) 章节级召回（推荐）
```python
from app.rag.retrieval.tool import retrieve_chapter_chunks, build_rag_context

chunks = await retrieve_chapter_chunks(
    query="变量是什么",
    course_code="python_basics",
    top_k=5,
    score_threshold=0.0,
    chapter_order=3
)

context = build_rag_context(chunks, max_context_chars=3000)
```

### 3) 按章节文件名召回
```python
chunks = await retrieve_chapter_chunks(
    query="变量是什么",
    course_code="python_basics",
    top_k=5,
    score_threshold=0.0,
    chapter_source_file="03_变量与数据类型.md"
)
```

## 输出说明
`retrieve_*` 返回结构化分块列表（`RagChunk`），包含：
- `chunk_id` 分块 ID
- `score` 相似度分数
- `text` 分块内容
- `source_file` 章节文件名
- `position` 章节位置
- `content_type` 内容类型

`build_rag_context` 返回可直接拼入提示词模板的上下文文本。

## 提示词模板接入示例
```python
messages = prompt_loader.get_messages(
    "ai_assistant",
    include_templates=["course_context"],
    course_content=context or "未检索到相关内容。"
)
```
