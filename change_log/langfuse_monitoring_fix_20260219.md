# Langfuse 监控修复 - 变更记录

**日期**: 2026-02-19  
**类型**: Bug 修复  
**影响范围**: LLM 调用监控、Embedding 监控、Rerank 监控

---

## 一、问题描述

### 1.1 现象

配置 Langfuse 环境变量后，LLM 调用可以正常工作，但 Langfuse 中的 trace 数据存在问题：

- **Input/Output 为空**：所有 `ai_chat` trace 的 input 和 output 字段都是 `{"args": null, "kwargs": {}}`
- **Latency 为 0**：耗时统计不正确
- **无法看到实际调用内容**：用户消息、LLM 返回都无法在 Langfuse 中查看

### 1.2 数据库验证

```sql
SELECT id, name, input, output FROM traces WHERE name = 'ai_chat';
-- 结果：input = {"args": null, "kwargs": {}}, output = null
```

---

## 二、根本原因分析

### 2.1 装饰器模式的问题

原代码使用 `@trace_llm_call` 装饰器：

```python
@trace_llm_call("ai_chat", tags=["assistant", "course"])
async def generate_stream():
    async for chunk in llm.chat_stream(messages_payload, ...):
        yield chunk.content
```

问题：

1. **装饰器捕获的是函数参数**：`generate_stream()` 没有参数，所以 `args` 和 `kwargs` 都是空的
2. **`messages_payload` 是闭包变量**：装饰器无法访问外层作用域的变量
3. **Async Generator 的特殊性**：`await func()` 返回的是 generator 对象，不会立即执行
4. **输出在流结束后才完整**：装饰器在函数返回时记录，此时流还未开始

### 2.2 相同问题的影响范围

| 文件 | 问题 |
|------|------|
| `app/api/learning.py` | `generate_stream()` 是 async generator |
| `app/rag/embedding/models.py` | `_do_encode()` 内部函数无参数 |
| `app/rag/retrieval/reranker.py` | `_do_rerank()` 内部函数无参数 |
| `app/tasks/jobs.py` | `_do_generate()` 内部函数无参数 |

### 2.3 Langfuse SDK 版本问题（已修复）

- 容器使用 Langfuse v2.95.11
- 原依赖 `langfuse>=2.0.0` 安装了 v3.x
- v3 的 API 不兼容（`client.trace()` 方法不存在）

---

## 三、修复方案

### 3.1 核心改动：装饰器 → 手动创建 Trace

将装饰器模式改为手动创建和管理 trace：

```python
# 修复前（装饰器模式）
@trace_llm_call("ai_chat", tags=["assistant"])
async def generate_stream():
    async for chunk in llm.chat_stream(messages):
        yield chunk.content

# 修复后（手动模式）
async def generate_stream():
    langfuse_client = _get_langfuse_client()
    trace = None
    start_time = dt.now()
    
    # 准备 trace 输入数据
    input_data = {
        "user_message": request.message,
        "chapter_id": request.chapter_id,
        "messages_count": len(messages_payload),
    }
    
    # 创建 trace
    if langfuse_client:
        trace = langfuse_client.trace(name="ai_chat", input=input_data, tags=["assistant"])
    
    full_response = ""
    error_occurred = None
    
    try:
        async for chunk in llm.chat_stream(messages_payload, ...):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content
    except Exception as e:
        error_occurred = str(e)
        yield f"Error: {e}"
    finally:
        # 记录 trace（在流结束后）
        if langfuse_client and trace:
            end_time = dt.now()
            output_data = {
                "response_length": len(full_response),
                "response_preview": full_response[:500],
            }
            if error_occurred:
                output_data["error"] = error_occurred
            
            trace.span(
                name="llm_call",
                input=input_data,
                output=output_data,
                start_time=start_time,
                end_time=end_time,
                metadata={"duration_ms": (end_time - start_time).total_seconds() * 1000},
            )
            trace.update(output=output_data)
            langfuse_client.flush()
```

### 3.2 关键点

1. **在流开始前创建 trace**：捕获完整的输入数据
2. **在 finally 中记录输出**：确保流结束后能记录完整响应
3. **使用 span 记录详情**：包含 input、output、start_time、end_time
4. **更新 trace 的 output**：通过 `trace.update()` 更新顶层输出
5. **强制 flush**：确保数据立即上报到 Langfuse

---

## 四、修改文件清单

### 4.1 `src/backend/app/api/learning.py`

**改动**：
- 移除 `@trace_llm_call` 装饰器
- 在 `generate_stream()` 内部手动创建和管理 trace
- 添加中文注释说明关键逻辑

### 4.2 `src/backend/app/rag/embedding/models.py`

**改动**：
- 移除 `_get_trace_embedding()` 辅助函数
- 重写 `_encode_with_tracing()` 方法，手动创建 trace
- 记录 `text_count`、`model`、`sample` 作为输入
- 记录 `embedding_count`、`dimension` 作为输出

### 4.3 `src/backend/app/rag/retrieval/reranker.py`

**改动**：
- 移除 `_get_trace_rerank()` 辅助函数
- 重写 `_rerank_with_tracing()` 方法，手动创建 trace
- 记录 `query`、`result_count` 作为输入
- 记录 `reranked_count` 作为输出

### 4.4 `src/backend/app/tasks/jobs.py`

**改动**：
- 移除 `_get_trace_decorator()` 辅助函数
- 添加 `_create_trace()` 和 `_finish_trace()` 辅助函数
- 重写 `generate_wordcloud()`、`generate_knowledge_graph()`、`generate_quiz()` 的 trace 逻辑

### 4.5 `src/backend/pyproject.toml`

**改动**：
- 限制 langfuse 版本：`"langfuse>=2.0.0,<3.0.0"`
- 确保与 Langfuse 容器 v2.x 兼容

### 4.6 `src/backend/Dockerfile`

**改动**：
- 修复 `uv.lock` 文件复制：`uv.lock*` → `uv.lock`
- 确保 lock 文件正确复制到容器

### 4.7 `src/backend/uv.lock`

**改动**：
- 重新生成 lock 文件，包含 `langfuse==2.60.10`

---

## 五、验证结果

### 5.1 Trace 数据验证

```sql
SELECT o.name, o.input, o.output
FROM observations o
JOIN traces t ON o.trace_id = t.id
WHERE t.name = 'ai_chat'
ORDER BY t.created_at DESC LIMIT 1;
```

结果：

```
name: llm_call
input: {
  "chapter_id": "c868b7cc-...",
  "user_message": "什么是RAG",
  "messages_count": 3
}
output: {
  "response_length": 596,
  "response_preview": "RAG 是 Retrieval Augmented Generation 的缩写..."
}
```

### 5.2 Langfuse UI 验证

访问 `http://localhost:3001/project/{project_id}/traces` 可以看到：

- ✅ 完整的用户消息
- ✅ LLM 响应预览（前 500 字符）
- ✅ 正确的耗时统计（~42 秒）
- ✅ Tags 正确显示（`assistant`, `course`）

---

## 六、最佳实践总结

### 6.1 何时使用装饰器

装饰器 `@trace_llm_call` 适用于：
- 普通函数（非 generator）
- 函数参数包含需要追踪的数据
- 非流式响应

### 6.2 何时使用手动 Trace

手动创建 trace 适用于：
- **Async Generator**（流式响应）
- **闭包变量**需要追踪（非函数参数）
- 需要**在 finally 中记录**完整输出
- 需要**精细控制** trace 的生命周期

### 6.3 代码模板

```python
from app.llm.langfuse_wrapper import _get_langfuse_client
from datetime import datetime as dt

async def my_llm_function(input_data):
    langfuse_client = _get_langfuse_client()
    trace = None
    start_time = dt.now()
    
    trace_input = {"query": input_data.query}
    
    if langfuse_client:
        trace = langfuse_client.trace(name="my_llm_call", input=trace_input, tags=["my_tag"])
    
    result = None
    error = None
    
    try:
        # 执行 LLM 调用
        result = await do_llm_call(input_data)
        return result
    except Exception as e:
        error = str(e)
        raise
    finally:
        # 记录 trace
        if langfuse_client and trace:
            end_time = dt.now()
            trace_output = {"result": result[:500] if result else None}
            if error:
                trace_output["error"] = error
            
            trace.span(
                name="llm_call",
                input=trace_input,
                output=trace_output,
                start_time=start_time,
                end_time=end_time,
                metadata={"duration_ms": (end_time - start_time).total_seconds() * 1000},
            )
            trace.update(output=trace_output)
            langfuse_client.flush()
```

---

## 七、后续工作

- [ ] 为 RAG 服务的 `retrieve()` 方法添加 trace
- [ ] 考虑将手动 trace 模式封装为可复用的上下文管理器
- [ ] 添加 trace 的 user_id 和 session_id 支持

---

**修复完成时间**: 2026-02-19 13:10
