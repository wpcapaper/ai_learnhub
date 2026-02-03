# RAG模块文档

## 概述

RAG (Retrieval-Augmented Generation) 模块为助学Agent提供课程内容检索功能，支持基于语义的文档检索，帮助Agent基于课程内容回答用户问题。

## 模块结构

```
rag/
├── chunking/          # 文档切割模块
│   ├── strategies.py # 切割策略（语义切割、固定大小切割）
│   ├── filters.py    # 内容过滤器
│   └── metadata.py   # 元数据定义
├── embedding/         # Embedding模块
│   ├── models.py     # Embedding模型封装
│   └── evaluator.py  # 模型评估工具
├── vector_store/      # 向量存储
│   ├── base.py       # 抽象接口
│   └── chroma.py     # ChromaDB实现
├── retrieval/         # 检索模块
│   ├── retriever.py  # 基础检索器
│   ├── reranker.py   # 重排序（Extra）
│   ├── hybrid.py     # 混合检索（Extra）
│   └── tool.py       # Agent工具
├── evaluation/        # 评估模块
│   ├── recall_tester.py # 召回测试工具
│   └── metrics.py    # 评估指标
├── multilingual/      # 多语言支持（Extra）
│   ├── detector.py   # 语言检测
│   └── query_expander.py # 查询扩展
└── service.py        # RAG服务层
```

## 功能特性

### Baseline功能

1. **文档切割策略**
   - 语义切割：按Markdown结构切割，保持语义完整
   - 固定大小切割：按字符数切割
   - 支持重叠窗口，提升召回率

2. **内容过滤**
   - 自动识别可做embedding的内容
   - 过滤纯代码、公式、图片等不适合embedding的内容

3. **Embedding模型支持**
   - `text2vec-base-chinese`: 中文基础模型
   - `bge-large-zh`: 中文大模型（推荐）
   - `multilingual-e5-large`: 多语言模型

4. **向量存储**
   - 基于ChromaDB的向量存储
   - 支持元数据过滤
   - 按课程组织collection

5. **检索工具**
   - 为Agent提供检索接口
   - 支持相似度阈值过滤
   - 返回格式化的检索结果

6. **召回测试工具**
   - 评估召回率、精确率、MRR等指标
   - 支持批量测试
   - 生成测试报告

### Extra功能

1. **多语言支持**
   - 自动语言检测
   - 支持中英文混合内容

2. **查询扩展**
   - 同义词扩展
   - LLM查询重写（可选）

3. **混合检索**
   - 向量检索 + 关键词检索
   - 加权融合结果

4. **重排序**
   - 使用交叉编码器提升精确度
   - 对Top-K结果重排序

## 使用方法

### 1. 初始化RAG服务

```python
from app.rag.service import RAGService

rag_service = RAGService(
    embedding_model_key="bge-large-zh",
    use_reranker=False,
    use_hybrid=False,
    use_query_expansion=False
)
```

### 2. 索引课程内容

```python
chunk_count = await rag_service.index_course_content(
    content=markdown_content,
    course_id="llm_basic",
    chapter_id="ch01",
    chapter_title="第一章 基础概念",
    clear_existing=False
)
```

### 3. 检索相关内容

```python
results = await rag_service.retrieve(
    query="什么是大语言模型？",
    course_id="llm_basic",
    top_k=5,
    score_threshold=0.5
)

for result in results:
    print(f"来源: {result.source}")
    print(f"相似度: {result.score:.3f}")
    print(f"内容: {result.text}\n")
```

### 4. 运行召回测试

```python
from app.rag.evaluation import RecallTester, TestCase

test_cases = [
    TestCase(
        query="什么是监督学习？",
        relevant_chunk_ids=["chunk_1", "chunk_2"]
    )
]

retriever = rag_service.get_retriever("llm_basic")
tester = RecallTester(retriever)

report = await tester.run_test(
    test_cases=test_cases,
    course_id="llm_basic",
    top_k=5
)

print(tester.generate_report(report))
```

## API接口

### 索引内容

```http
POST /api/rag/index
Content-Type: application/json

{
  "content": "# 课程内容...",
  "course_id": "llm_basic",
  "chapter_id": "ch01",
  "chapter_title": "第一章",
  "clear_existing": false
}
```

### 检索内容

```http
POST /api/rag/retrieve
Content-Type: application/json

{
  "query": "什么是大语言模型？",
  "course_id": "llm_basic",
  "top_k": 5,
  "score_threshold": 0.5
}
```

### 运行召回测试

```http
POST /api/rag/test/recall
Content-Type: application/json

{
  "test_cases": [
    {
      "query": "什么是监督学习？",
      "relevant_chunk_ids": ["chunk_1", "chunk_2"]
    }
  ],
  "course_id": "llm_basic",
  "top_k": 5
}
```

## 配置选项

### Embedding模型选择

- `text2vec-base-chinese`: 轻量级，速度快
- `bge-large-zh`: 性能优秀（推荐）
- `multilingual-e5-large`: 支持多语言

### 切割策略参数

```python
SemanticChunkingStrategy(
    min_chunk_size=100,    # 最小chunk大小
    max_chunk_size=1000,   # 最大chunk大小
    overlap_size=200      # 重叠大小
)
```

## 性能优化建议

1. **模型选择**: 根据场景选择模型，中文场景推荐`bge-large-zh`
2. **切割策略**: 优先使用语义切割，保证语义完整性
3. **重叠窗口**: 适当设置重叠大小（20-30%）提升召回率
4. **重排序**: 对精确度要求高的场景启用重排序
5. **混合检索**: 结合关键词检索提升特定场景的召回率

## 注意事项

1. 首次使用需要下载Embedding模型，可能需要较长时间
2. ChromaDB数据存储在`data/chroma`目录
3. 索引大量内容时注意内存使用
4. 建议定期运行召回测试评估效果
