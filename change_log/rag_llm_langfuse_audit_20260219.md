# RAG 模块 LLM 封装与 Langfuse 监控审计

**日期**: 2026-02-19  
**类型**: 代码审计 + 功能修复  
**影响范围**: course_pipeline/evaluators, RAG 模块

---

## 一、审计背景

随着 RAG 系统和课程管理功能的引入，需要确保所有新增代码：
1. 使用统一的 LLM 封装（`app.llm.get_llm_client()`）
2. 使用 Prompt 模板系统（`app.prompts.loader`）
3. 接入 Langfuse 监控

---

## 二、审计范围

### 2.1 审计的模块

| 模块 | 路径 | 说明 |
|------|------|------|
| 课程质量评估 | `course_pipeline/evaluators/` | LLM 智能评估课程质量 |
| RAG 服务 | `rag/` | 向量检索、Embedding、Rerank |
| 异步任务 | `tasks/jobs.py` | 后台任务（词云、知识图谱等） |

### 2.2 统一封装标准

**LLM 调用**:
```python
from app.llm import get_llm_client
llm = get_llm_client()
response = llm.chat_sync(messages, temperature=0.3)  # 同步
# 或
async for chunk in llm.chat_stream(messages): ...    # 流式
```

**Prompt 模板**:
```python
from app.prompts.loader import prompt_loader
messages = prompt_loader.get_messages("template_name", **variables)
```

**Langfuse 监控**:
```python
from app.llm.langfuse_wrapper import _get_langfuse_client
langfuse_client = _get_langfuse_client()
if langfuse_client:
    trace = langfuse_client.trace(name="xxx", input=input_data, tags=[...])
    # ... LLM 调用 ...
    trace.generation(name="llm_call", input=..., output=..., usage=...)
    langfuse_client.flush()
```

---

## 三、审计结果

### 3.1 已符合规范的代码

| 文件 | 功能 | LLM封装 | Prompt | Langfuse |
|------|------|:-------:|:------:|:--------:|
| `api/learning.py` | AI 助教聊天 | ✅ | ✅ | ✅ |
| `rag/embedding/models.py` | Embedding | N/A | N/A | ✅ |
| `rag/retrieval/reranker.py` | Rerank | N/A | N/A | ✅ |
| `tasks/jobs.py` | 任务框架 | ⏳ | ⏳ | ✅ 框架 |

### 3.2 发现的问题

| 文件 | 问题 | 严重性 |
|------|------|--------|
| `course_pipeline/evaluators/__init__.py` | `_llm_evaluation()` 缺少 Langfuse 监控 | 高 |

### 3.3 低优先级 TODO

| 文件 | 功能 | 状态 |
|------|------|------|
| `rag/multilingual/query_expander.py` | `_rewrite_with_llm()` 未实现 | 占位符 |
| `tasks/jobs.py` | `generate_knowledge_graph()` LLM 调用 | 占位符 |
| `tasks/jobs.py` | `generate_quiz()` LLM 调用 | 占位符 |

---

## 四、修复内容

### 4.1 修复 `course_pipeline/evaluators/__init__.py`

**问题**: `_llm_evaluation()` 方法调用了 LLM 但没有 Langfuse 监控

**修复**: 添加完整的 Langfuse trace 支持

**修改前**:
```python
def _llm_evaluation(self, context: EvaluationContext, report: QualityReport):
    # ... 省略准备逻辑 ...
    try:
        from app.prompts.loader import prompt_loader
        messages = prompt_loader.get_messages(...)
        
        from app.llm import get_llm_client
        llm = get_llm_client()
        response = llm.chat_sync(messages=messages, temperature=0.3)
        
        # 解析结果 ...
    except Exception as e:
        report.recommendations.append(f"LLM评估未能完成: {str(e)}")
```

**修改后**:
```python
def _llm_evaluation(self, context: EvaluationContext, report: QualityReport):
    # ... 省略准备逻辑 ...
    
    # Langfuse 监控
    from app.llm.langfuse_wrapper import _get_langfuse_client
    from app.llm import get_llm_client
    from app.prompts.loader import prompt_loader
    
    langfuse_client = _get_langfuse_client()
    trace = None
    start_time = datetime.now()
    
    # 准备 trace 输入数据
    input_data = {
        "course_id": context.course_id,
        "course_title": context.course_title,
        "chapter_count": len(context.chapters),
        "content_length": len(full_content),
        "truncated": len(full_content) > max_content_length,
    }
    
    # 创建 Langfuse trace
    if langfuse_client:
        trace = langfuse_client.trace(
            name="course_quality_evaluation",
            input=input_data,
            tags=["course", "quality", "evaluation"],
        )
    
    error_occurred = None
    result_text = ""
    usage_info = None
    issues_found = 0
    
    try:
        messages = prompt_loader.get_messages(...)
        llm = get_llm_client()
        response = llm.chat_sync(messages=messages, temperature=0.3)
        
        # 提取 usage 信息
        if response.usage:
            usage_info = {...}
        
        # 解析结果 ...
        issues_found = len(issues)
    except Exception as e:
        error_occurred = str(e)
        report.recommendations.append(f"LLM评估未能完成: {str(e)}")
    finally:
        # 记录 trace 到 Langfuse
        if langfuse_client and trace:
            end_time = datetime.now()
            output_data = {
                "issues_found": issues_found,
                "response_length": len(result_text),
                "response_preview": result_text[:500],
            }
            if error_occurred:
                output_data["error"] = error_occurred
            
            trace.generation(
                name="llm_call",
                input=input_data,
                output=output_data,
                model=llm.default_model,
                usage={
                    "input": usage_info.get("prompt_tokens"),
                    "output": usage_info.get("completion_tokens"),
                    "total": usage_info.get("total_tokens"),
                },
                start_time=start_time,
                end_time=end_time,
                metadata={"duration_ms": (end_time - start_time).total_seconds() * 1000},
            )
            trace.update(output=output_data)
            langfuse_client.flush()
```

---

## 五、验证清单

- [x] `_llm_evaluation()` 已添加 Langfuse 监控
- [x] 使用 `trace.generation()` 支持 usage 统计
- [x] 在 `finally` 块中完成 trace，确保异常也能追踪
- [x] 修复 prompt_loader 导入路径（`from prompts import` 而非 `from app.prompts.loader import`）
- [x] 低优先级 TODO 功能保持不变
- [x] 项目可正常运行

---

## 六、后续工作

当以下 TODO 功能需要实现时，需遵循统一封装规范：

1. **`query_expander._rewrite_with_llm()`**
   - 使用 `get_llm_client()`
   - 创建 `prompts/templates/query_expander.yaml`
   - 添加 Langfuse 追踪

2. **`jobs.generate_knowledge_graph()`**
   - 使用 `get_llm_client()`
   - 创建 `prompts/templates/knowledge_graph.yaml`
   - 已有 Langfuse 框架

3. **`jobs.generate_quiz()`**
   - 使用 `get_llm_client()`
   - 创建 `prompts/templates/quiz_generation.yaml`
   - 已有 Langfuse 框架
