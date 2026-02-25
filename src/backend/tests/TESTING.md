# 单元测试运行与覆盖链路说明

## 运行方式
在后端目录执行：
```
PYTHONPATH="/Users/crazzie/Codes/aie55_llm5_learnhub/src/backend" python -m pytest
```

## 覆盖链路说明
### 1) `tests/test_chroma_vector_store.py`
- 覆盖 Chroma 向量存储基础 CRUD 与检索行为。
- 关联链路：RAG 向量存储适配层。

### 2) `tests/test_course_lifecycle.py`
- 覆盖课程从本地到数据库的导入流程。
- 关联链路：课程导入、课程目录扫描与 DB 写入。

### 3) `tests/test_course_refactor.py`
- 覆盖课程目录结构调整后的管理端 API 行为。
- 关联链路：课程目录路径解析、课程列表接口。

### 4) `tests/test_index_tasks.py`
- 覆盖异步任务函数：
  - `index_chapter`：章节索引、章节配置更新
  - `index_course`：批量索引、锁控制、清理策略
  - `generate_wordcloud`：课程/章节词云生成
  - `generate_knowledge_graph`：知识图谱任务壳
  - `generate_quiz`：Quiz 生成任务壳

### 5) `tests/test_rag_service.py`
- 覆盖 RAG 核心服务：索引、检索、集合管理与召回结果结构。
- 关联链路：RAGService 与 retrieval 逻辑。

### 6) `tests/test_sync_functionality.py`
- 覆盖同步相关流程与任务队列逻辑。
- 关联链路：任务队列、同步任务状态。
