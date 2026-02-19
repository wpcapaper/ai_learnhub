# LLM 架构重构 - 变更记录

**日期**: 2026-02-19  
**类型**: 架构重构  
**影响范围**: 后端 LLM 调用、监控、异步任务

---

## 一、变更概述

本次重构主要完成以下工作：

1. **LLM 调用封装** - 统一 LLM 调用接口，支持 Langfuse 监控
2. **Langfuse 集成** - LLM/Embedding/Rerank 调用追踪
3. **Redis Queue 异步任务框架** - 为任务型 Agent 做准备
4. **Docker 基础设施** - Redis + Langfuse 自托管

---

## 二、新增文件

### 2.1 LLM 封装层 (`src/backend/app/llm/`)

```
app/llm/
├── __init__.py           # 统一导出接口
├── base.py               # LLM 客户端抽象基类
├── openai_client.py      # OpenAI 兼容客户端实现
├── langfuse_wrapper.py   # Langfuse 监控装饰器
└── config.py             # LLM 配置管理
```

**核心类**：

| 类名 | 功能 |
|------|------|
| `LLMClient` | 抽象基类，定义统一接口 |
| `OpenAIClient` | OpenAI/DeepSeek 等兼容客户端 |
| `ChatResponse` | 非流式响应数据类 |
| `StreamChunk` | 流式响应块数据类 |

**使用示例**：

```python
from app.llm import get_llm_client, trace_llm_call

# 获取 LLM 客户端
llm = get_llm_client()

# 非流式调用
response = await llm.chat([{"role": "user", "content": "Hello"}])
print(response.content)

# 流式调用（用于 SSE）
async for chunk in llm.chat_stream(messages):
    yield chunk.content

# 使用 Langfuse 追踪
@trace_llm_call("ai_chat", tags=["assistant"])
async def my_chat_function(messages):
    return await llm.chat(messages)
```

### 2.2 异步任务框架 (`src/backend/app/tasks/`)

```
app/tasks/
├── __init__.py    # 模块导出
├── base.py        # AsyncTask, TaskStatus, TaskType
├── queue.py       # 队列管理 (get_queue, enqueue_task)
└── jobs.py        # 任务函数 (占位实现)
```

**任务类型**：

| TaskType | 描述 | 状态 |
|----------|------|------|
| `WORDCLOUD` | 词云生成 | 占位 |
| `KNOWLEDGE_GRAPH` | 知识图谱生成 | 占位 |
| `QUIZ_GENERATION` | Quiz 自动生成 | 占位 |

**使用示例**：

```python
from app.tasks import enqueue_task, generate_quiz

# 入队任务
task_id = enqueue_task(
    generate_quiz,
    chapter_id="ch01",
    course_id="course1",
    config={"count": 5}
)
```

---

## 三、修改文件

### 3.1 `src/backend/app/api/learning.py`

**变更**：
- 移除直接使用 `AsyncOpenAI`
- 改用 `get_llm_client()` 获取统一客户端
- 自动获得 Langfuse 追踪支持

**迁移前**：
```python
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=api_key, base_url=base_url)
stream = await client.chat.completions.create(...)
```

**迁移后**：
```python
from app.llm import get_llm_client
llm = get_llm_client()
async for chunk in llm.chat_stream(messages, temperature=0.7):
    yield chunk.content
```

### 3.2 `src/backend/app/rag/embedding/models.py`

**变更**：
- 添加 `_get_trace_embedding()` 辅助函数
- `OpenAIEmbedder.encode()` 方法集成 Langfuse 追踪

### 3.3 `src/backend/app/rag/retrieval/reranker.py`

**变更**：
- 添加 `_get_trace_rerank()` 辅助函数
- `Reranker.rerank()` 方法集成 Langfuse 追踪

### 3.4 `src/backend/pyproject.toml`

**新增依赖**：
```toml
# LLM 监控
"langfuse>=2.0.0",

# 异步任务队列
"redis>=5.0.0",
"rq>=1.15.0",
```

### 3.5 `docker-compose.yml`

**新增服务**：

| 服务 | 镜像 | 端口 | 用途 |
|------|------|------|------|
| `redis` | redis:7-alpine | 6379 | RQ 任务队列 |
| `langfuse` | langfuse/langfuse:2 | 3001 | LLM 监控 |
| `langfuse-db` | postgres:15-alpine | - | Langfuse 数据库 |

**移除服务**：
- `clickhouse` (v2 版本不需要)

---

## 四、配置说明

### 4.1 环境变量

**LLM 配置**（已有）：
```env
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

**Langfuse 配置**（新增）：
```env
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=http://localhost:3001
# 或使用云端：https://cloud.langfuse.com
```

**Redis 配置**（新增）：
```env
REDIS_URL=redis://redis:6379/0
```

### 4.2 Langfuse 启用条件

Langfuse 监控在以下条件满足时自动启用：
1. `LANGFUSE_PUBLIC_KEY` 和 `LANGFUSE_SECRET_KEY` 都已配置
2. 未设置 `LANGFUSE_ENABLED=false`

---

## 五、Langfuse 使用指南

### 5.1 首次设置

1. 启动服务：
```bash
docker-compose up -d
```

2. 访问 http://localhost:3001 创建账号

3. 在 Settings → Projects 创建项目

4. 获取 API Keys 并配置到 `.env`

5. 重启后端：
```bash
docker-compose restart backend
```

### 5.2 功能支持

| 功能 | v2 支持 | 说明 |
|------|---------|------|
| LLM 调用追踪 | ✅ | 自动记录 prompt/response |
| Embedding 追踪 | ✅ | 记录文本数量和维度 |
| Rerank 追踪 | ✅ | 记录查询和文档数 |
| Prompt 管理 | ✅ | 版本控制和 A/B 测试 |
| 成本统计 | ✅ | Token 使用量统计 |

---

## 六、架构文档更新

`change_intent/ai_agent_architecture_evaluation.md` 已更新，包含：

- 确认原架构设计合理
- 更新技术选型：RQ + Langfuse (v2)
- 新增 LLM 封装层设计
- 更新实施路线图

---

## 七、后续工作

### 7.1 待完成任务

- [ ] 实现 `generate_wordcloud()` 实际逻辑
- [ ] 实现 `generate_knowledge_graph()` 实际逻辑
- [ ] 实现 `generate_quiz()` 实际逻辑
- [ ] 创建异步任务 API 端点
- [ ] 前端任务监控界面

### 7.2 升级到 Langfuse v3（可选）

如需升级到 v3，需要额外部署：
- ClickHouse
- MinIO
- Redis（Langfuse 专用）
- Worker 容器

参考 `docker-compose.langfuse.yml` 配置。

---

## 八、验证清单

- [x] LLM 封装层可正常调用 DeepSeek
- [x] Langfuse 可追踪 LLM 调用
- [x] Embedding 调用被追踪
- [x] Rerank 调用被追踪
- [x] Redis 容器正常运行
- [x] Langfuse v2 容器正常运行
- [x] 原有功能不受影响
