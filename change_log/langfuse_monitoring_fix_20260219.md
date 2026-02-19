# Langfuse 监控修复 - 变更记录

**日期**: 2026-02-19  
**类型**: Bug 修复 + 功能增强  
**影响范围**: LLM 调用监控、Embedding 监控、Rerank 监控

---

## 一、问题描述

### 1.1 现象

配置 Langfuse 环境变量后，LLM 调用可以正常工作，但 Langfuse 中的 trace 数据存在问题：

- **Input/Output 为空**：所有 `ai_chat` trace 的 input 和 output 字段都是 `{"args": null, "kwargs": {}}`
- **Latency 为 0**：耗时统计不正确
- **Usage 为 0**：Token 统计不显示
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

### 2.2 Usage 统计为 0 的原因

1. **流式 API 默认不返回 usage**：OpenAI 兼容 API 需要设置 `stream_options={"include_usage": True}`
2. **使用了 span 而非 generation**：Langfuse 只对 `generation` 类型自动计算 usage
3. **未手动传入 usage 数据**：即使有 usage 数据也需要显式传给 Langfuse

### 2.3 相同问题的影响范围

| 文件 | 问题 |
|------|------|
| `app/api/learning.py` | `generate_stream()` 是 async generator |
| `app/rag/embedding/models.py` | `_do_encode()` 内部函数无参数 |
| `app/rag/retrieval/reranker.py` | `_do_rerank()` 内部函数无参数 |
| `app/tasks/jobs.py` | `_do_generate()` 内部函数无参数 |

### 2.4 Langfuse SDK 版本问题（已修复）

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
    
    # 获取用户信息
    # 注意：当前开发阶段使用 nickname 便于在 Langfuse 中直观识别用户
    # 后续生产化应改为使用 user_id，因为 nickname 可能重复或变更
    user_nickname = None
    if request.user_id:
        user = db.query(User).filter(User.id == request.user_id).first()
        if user:
            user_nickname = user.nickname
    
    # 准备 trace 输入数据
    input_data = {
        "user_message": request.message,
        "chapter_id": request.chapter_id,
        "messages_count": len(messages_payload),
    }
    
    # 创建 trace（包含 user 信息）
    if langfuse_client:
        trace = langfuse_client.trace(
            name="ai_chat",
            input=input_data,
            user_id=user_nickname or request.user_id,
            tags=["assistant"],
        )
    
    full_response = ""
    usage_info = None  # 收集 token 使用信息
    error_occurred = None
    
    try:
        async for chunk in llm.chat_stream(messages_payload, ...):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content
            elif chunk.usage:
                usage_info = chunk.usage  # 最后一个块包含 usage
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
            
            # 使用 generation 类型记录 LLM 调用（支持 usage 统计）
            trace.generation(
                name="llm_call",
                input=input_data,
                output=output_data,
                model=llm.default_model,
                usage={
                    "input": usage_info.get("prompt_tokens"),
                    "output": usage_info.get("completion_tokens"),
                    "total": usage_info.get("total_tokens"),
                } if usage_info else None,
                start_time=start_time,
                end_time=end_time,
                metadata={"duration_ms": (end_time - start_time).total_seconds() * 1000},
            )
            trace.update(output=output_data)
            langfuse_client.flush()
```

### 3.2 启用流式 API Usage 返回

修改 `openai_client.py`：

```python
params = {
    "model": model,
    "messages": messages,
    "temperature": temperature,
    "stream": True,
    "stream_options": {"include_usage": True},  # 关键：启用 usage 返回
}

# 在最后一个块中提取 usage
if hasattr(chunk, 'usage') and chunk.usage:
    yield StreamChunk(
        content="",
        usage={
            "prompt_tokens": chunk.usage.prompt_tokens,
            "completion_tokens": chunk.usage.completion_tokens,
            "total_tokens": chunk.usage.total_tokens,
        },
    )
```

### 3.3 关键点

1. **在流开始前创建 trace**：捕获完整的输入数据
2. **在 finally 中记录输出**：确保流结束后能记录完整响应
3. **使用 generation 而非 span**：支持 usage 统计
4. **启用 stream_options**：获取 API 返回的 usage 信息
5. **添加 user_id**：便于按用户追踪
6. **强制 flush**：确保数据立即上报到 Langfuse

---

## 四、修改文件清单

### 4.1 `src/backend/app/llm/base.py`

**改动**：
- `StreamChunk` 添加 `usage` 字段

### 4.2 `src/backend/app/llm/openai_client.py`

**改动**：
- 添加 `stream_options={"include_usage": True}` 启用 usage 返回
- 在流末尾提取 usage 信息并返回

### 4.3 `src/backend/app/api/learning.py`

**改动**：
- 移除 `@trace_llm_call` 装饰器
- 在 `generate_stream()` 内部手动创建和管理 trace
- 添加 user_id（使用 nickname 便于识别）
- 收集 usage 信息并传给 Langfuse
- 使用 `trace.generation()` 替代 `trace.span()`
- 添加中文注释说明关键逻辑

### 4.4 `src/backend/app/rag/embedding/models.py`

**改动**：
- 移除 `_get_trace_embedding()` 辅助函数
- 重写 `_encode_with_tracing()` 方法，手动创建 trace
- 记录 `text_count`、`model`、`sample` 作为输入
- 记录 `embedding_count`、`dimension` 作为输出

### 4.5 `src/backend/app/rag/retrieval/reranker.py`

**改动**：
- 移除 `_get_trace_rerank()` 辅助函数
- 重写 `_rerank_with_tracing()` 方法，手动创建 trace
- 记录 `query`、`result_count` 作为输入
- 记录 `reranked_count` 作为输出

### 4.6 `src/backend/app/tasks/jobs.py`

**改动**：
- 移除 `_get_trace_decorator()` 辅助函数
- 添加 `_create_trace()` 和 `_finish_trace()` 辅助函数
- 重写 `generate_wordcloud()`、`generate_knowledge_graph()`、`generate_quiz()` 的 trace 逻辑

### 4.7 `src/backend/pyproject.toml`

**改动**：
- 限制 langfuse 版本：`"langfuse>=2.0.0,<3.0.0"`
- 确保与 Langfuse 容器 v2.x 兼容

### 4.8 `src/backend/Dockerfile`

**改动**：
- 修复 `uv.lock` 文件复制：`uv.lock*` → `uv.lock`
- 确保 lock 文件正确复制到容器

### 4.9 `src/backend/uv.lock`

**改动**：
- 重新生成 lock 文件，包含 `langfuse==2.60.10`

---

## 五、验证结果

### 5.1 Trace 数据验证

```sql
SELECT 
    t.id, t.name, t.user_id, 
    o.model, o.prompt_tokens, o.completion_tokens, o.total_tokens
FROM traces t
LEFT JOIN observations o ON o.trace_id = t.id AND o.name = 'llm_call'
WHERE t.name = 'ai_chat'
ORDER BY t.created_at DESC LIMIT 1;
```

结果：

```
id: 1e36d8c7-d36d-4c54-8e89-27db8cf739a3
name: ai_chat
user_id: (nickname 或 user_id)
model: glm-5
prompt_tokens: 1941
completion_tokens: 384
total_tokens: 2325
```

### 5.2 Langfuse UI 验证

访问 `http://localhost:3001/project/{project_id}/traces` 可以看到：

- ✅ 完整的用户消息
- ✅ 完整的 system_prompt（包含课程内容片段）
- ✅ LLM 响应预览（前 500 字符）
- ✅ 正确的耗时统计
- ✅ Token 使用量（prompt_tokens、completion_tokens、total_tokens）
- ✅ Tags 正确显示（`assistant`, `course`）
- ✅ User 信息（便于按用户追踪）

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
- 需要**usage 统计**

### 6.3 代码模板

```python
from app.llm.langfuse_wrapper import _get_langfuse_client
from datetime import datetime as dt

async def my_llm_function(messages_payload, user_id=None):
    langfuse_client = _get_langfuse_client()
    trace = None
    start_time = dt.now()
    
    # 提取 system prompt 和 user messages
    system_prompt = None
    user_messages = []
    for msg in messages_payload:
        if msg.get("role") == "system":
            system_prompt = msg.get("content", "")
        else:
            user_messages.append({
                "role": msg.get("role"),
                "content": msg.get("content", "")[:200],  # 截断避免过长
            })
    
    # 准备 trace 输入数据（包含完整的 prompt 信息）
    trace_input = {
        "user_message": user_messages[-1].get("content") if user_messages else None,
        "system_prompt": system_prompt,  # 完整的 system prompt
        "conversation_history_count": len(user_messages) - 1,
    }
    
    if langfuse_client:
        trace = langfuse_client.trace(
            name="my_llm_call",
            input=trace_input,
            user_id=user_id,
            tags=["my_tag"],
        )
    
    result = None
    usage_info = None
    error = None
    
    try:
        async for chunk in llm.chat_stream(messages_payload, ...):
            if chunk.content:
                result += chunk.content
                yield chunk.content
            elif chunk.usage:
                usage_info = chunk.usage
    except Exception as e:
        error = str(e)
        raise
    finally:
        if langfuse_client and trace:
            end_time = dt.now()
            trace_output = {
                "response_length": len(result),
                "response_preview": result[:500] if result else None,
            }
            if error:
                trace_output["error"] = error
            
            # 使用 generation 支持 usage 统计
            trace.generation(
                name="llm_call",
                input=trace_input,
                output=trace_output,
                model="your-model-name",
                usage={
                    "input": usage_info.get("prompt_tokens") if usage_info else None,
                    "output": usage_info.get("completion_tokens") if usage_info else None,
                    "total": usage_info.get("total_tokens") if usage_info else None,
                },
                start_time=start_time,
                end_time=end_time,
                metadata={"duration_ms": (end_time - start_time).total_seconds() * 1000},
            )
            trace.update(output=trace_output)
            langfuse_client.flush()
```

### 6.4 User ID 使用建议

```python
# 当前开发阶段：使用 nickname 便于识别
user_id=user_nickname or request.user_id

# 后续生产化：应改为使用稳定的 user_id
# user_id=request.user_id  # nickname 可能重复或变更
```

---

## 七、后续工作

- [x] ~~添加 trace 的 user_id 支持~~ ✅ 已完成
- [x] ~~添加 usage 统计~~ ✅ 已完成
- [ ] 为 RAG 服务的 `retrieve()` 方法添加 trace
- [ ] 考虑将手动 trace 模式封装为可复用的上下文管理器
- [ ] 生产化时将 user_id 从 nickname 改为实际 user_id

---

**修复完成时间**: 2026-02-19 13:10  
**Usage & User 增强**: 2026-02-19 13:25
