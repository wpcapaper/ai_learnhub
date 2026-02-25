# AILearn Hub 架构文档

> 本文档描述 AILearn Hub 的系统架构、模块职责、核心流程和关键设计决策，帮助开发者快速理解项目结构并进行扩展。

---

## 目录

1. [概述](#1-概述)
2. [系统架构](#2-系统架构)
3. [核心领域概念](#3-核心领域概念)
4. [后端架构](#4-后端架构)
5. [前端架构](#5-前端架构)
6. [核心流程](#6-核心流程)
7. [架构决策记录](#7-架构决策记录)
8. [扩展指南](#8-扩展指南)
9. [术语表](#9-术语表)

---

## 1. 概述

### 1.1 项目定位

AILearn Hub 是一套基于**艾宾浩斯遗忘曲线**的 AI 智能学习系统，融合 **RAG（检索增强生成）** 与 **Agent 框架**，实现从课程内容导入、知识库构建到学习/复习闭环的全流程能力。

### 1.2 架构特征

- **架构模式**：模块化分层单体（Modular Layered Monolith）
- **核心特点**：
  - 科学记忆调度（9阶段艾宾浩斯算法）
  - 版本化 RAG 知识库管理
  - 技能注册型 Agent 框架 + SSE 流式输出
  - 轮次制学习进度管理

### 1.3 系统边界

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AILearn Hub 系统                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │  Learner    │  │   Admin     │  │        Backend API          │  │
│  │  Frontend   │  │  Frontend   │  │  (FastAPI + Services)       │  │
│  │  (Next.js)  │  │  (Next.js)  │  │                             │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────────┬──────────────┘  │
│         │                │                        │                  │
│         └────────────────┴────────────────────────┘                  │
│                           HTTP/SSE                                   │
├─────────────────────────────────────────────────────────────────────┤
│                        基础设施层                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ SQLite/  │ │ ChromaDB │ │  Redis   │ │ Langfuse │ │   LLM    │   │
│  │PostgreSQL│ │(向量存储) │ │  Queue   │ │ (监控)   │ │ Provider │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 系统架构

### 2.1 容器视图

系统由以下主要容器组成：

| 容器 | 技术栈 | 职责 |
|------|--------|------|
| **Backend** | FastAPI + SQLAlchemy | REST API、业务逻辑、RAG、Agent |
| **Worker** | Python + RQ | 异步任务处理（索引、导入、评估） |
| **Frontend** | Next.js 16 + React 19 | 学习端用户界面 |
| **Admin Frontend** | Next.js | 管理端界面（知识库管理、优化） |
| **Redis** | Redis 7 | 任务队列、缓存 |
| **Langfuse** | Langfuse 2 | LLM 调用监控与链路追踪 |

### 2.2 技术栈选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **Web 框架** | FastAPI | 异步支持、自动文档、类型验证 |
| **ORM** | SQLAlchemy | 成熟稳定、支持多种数据库 |
| **数据库** | SQLite / PostgreSQL | 开发便捷 / 生产可靠 |
| **前端框架** | Next.js 16 | SSR、App Router、自动代码分割 |
| **UI 库** | React 19 + Tailwind CSS 4 | 组件化、原子化 CSS |
| **向量数据库** | ChromaDB | 轻量级、支持元数据过滤、版本管理 |
| **任务队列** | Redis Queue | 简单可靠、与 FastAPI 集成良好 |
| **可观测性** | Langfuse | LLM 专用监控、链路追踪 |

---

## 3. 核心领域概念

### 3.1 学习模型

```
┌─────────────────────────────────────────────────────────────┐
│                     学习领域模型                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Course (课程)                                             │
│      ├── QuestionSet (题集)                                 │
│      │      └── Question (题目)                             │
│      │                                                      │
│   User (用户)                                               │
│      ├── UserCourseProgress (课程进度)                      │
│      │      └── current_round (当前轮次)                    │
│      │                                                      │
│      └── UserLearningRecord (学习记录)                      │
│             ├── review_stage (复习阶段: 0-8)                │
│             ├── next_review_time (下次复习时间)             │
│             └── completed_in_current_round (当前轮次完成)   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 艾宾浩斯 9 阶段复习系统

| 阶段 | 名称 | 复习间隔 | 说明 |
|------|------|---------|------|
| 0 | NEW | - | 新题，未学习 |
| 1 | LEVEL_1 | 30 分钟 | 短期记忆强化 |
| 2 | LEVEL_2 | 12 小时 | 中期记忆巩固 |
| 3 | LEVEL_3 | 1 天 | 长期记忆开始 |
| 4 | LEVEL_4 | 2 天 | 记忆稳定性提升 |
| 5 | LEVEL_5 | 4 天 | 持续强化 |
| 6 | LEVEL_6 | 7 天 | 一周复习节点 |
| 7 | LEVEL_7 | 15 天 | 长期记忆确立 |
| 8 | MASTERED | ∞ | 已掌握 |

**规则**：
- 答对 → 进入下一阶段
- 答错 → 回到第 1 阶段

### 3.3 轮次制学习

轮次（Round）是课程级别的进度管理机制：
- 用户完成一轮学习后可开启新一轮
- 每轮学习中，题目通过 `completed_in_current_round` 标记
- 新轮次开始时重置标记，允许重复学习

### 3.4 RAG 版本管理

```
Course
  └── kb_version: 1, 2, 3...
        └── Collection: course_{code}_{kb_version}
              └── Chunks with metadata
```

- 每个 `kb_version` 对应一个独立的 ChromaDB Collection
- 版本切换通过更新 `course.kb_version` 实现，原子化切换
- 支持无缝更新和回滚

---

## 4. 后端架构

### 4.1 分层结构

```
┌─────────────────────────────────────────────────────────────┐
│                    Backend Layered Architecture              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    API Layer (api/)                   │   │
│  │   请求验证 │ 认证处理 │ 响应格式化 │ 调用 Service      │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Service Layer (services/)              │   │
│  │   用例编排 │ 事务管理 │ 调用 Core/Models/RAG/Agent   │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                │
│  ┌────────────────────┬────────────────────────────────┐   │
│  │   Core (core/)     │        Models (models/)        │   │
│  │   领域策略          │        数据模型                │   │
│  │   艾宾浩斯算法      │        SQLAlchemy ORM         │   │
│  └────────────────────┴────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Infrastructure Adapters                  │   │
│  │  rag/ │ agent/ │ llm/ │ tasks/ │ course_pipeline/   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 模块职责

| 模块 | 路径 | 职责 |
|------|------|------|
| **api/** | `app/api/` | HTTP 端点定义、请求验证、响应格式化 |
| **services/** | `app/services/` | 业务用例编排、事务管理 |
| **core/** | `app/core/` | 领域策略（艾宾浩斯算法）、数据库配置 |
| **models/** | `app/models/` | 数据模型定义、表关系 |
| **rag/** | `app/rag/` | RAG 能力：切分、嵌入、检索、评估 |
| **agent/** | `app/agent/` | Agent 框架：技能注册、流式执行 |
| **llm/** | `app/llm/` | LLM 网关：统一调用接口、Langfuse 追踪 |
| **tasks/** | `app/tasks/` | 异步任务：Redis Queue 封装 |
| **course_pipeline/** | `app/course_pipeline/` | 课程转换：Markdown/Word → 结构化数据 |

### 4.3 RAG 子模块

```
rag/
├── chunking/       # 文档切割策略（语义切割、固定大小）
├── embedding/      # Embedding 模型封装（OpenAI/BGE/E5）
├── vector_store/   # 向量存储（ChromaDB 适配器）
├── retrieval/      # 检索器 + Rerank 重排序
├── evaluation/     # 召回测试与评估
└── multilingual/   # 多语言支持
```

### 4.4 Agent 框架

```
agent/
├── base.py         # Agent 基类、SkillRegistry、装饰器
├── events.py       # SSE 事件类型定义
└── rag_optimizer.py # RAG 优化 Agent 实现
```

**技能注册模式**：
```python
class MyAgent(Agent):
    @skill("analyze", description="分析数据")
    def analyze_data(self, data: str) -> dict:
        return {"result": "analyzed"}
```

---

## 5. 前端架构

### 5.1 学习端 (Frontend)

```
src/frontend/
├── app/                    # App Router 页面
│   ├── page.tsx           # 首页（课程选择）
│   ├── quiz/              # 刷题模式
│   ├── exam/              # 考试模式
│   ├── mistakes/          # 错题本
│   ├── review/            # 复习模式
│   └── learning/          # 课程学习（Markdown 阅读器）
├── components/            # 可复用组件
│   └── LaTeXRenderer.tsx  # KaTeX 公式渲染
└── lib/
    └── api.ts             # API Client 封装
```

### 5.2 管理端 (Admin Frontend)

```
src/admin-frontend/
├── app/
│   ├── page.tsx           # 管理首页
│   ├── knowledge-base/    # 知识库管理
│   ├── optimization/      # 课程优化（RAG Optimizer Agent）
│   ├── rag-test/          # RAG 召回测试
│   └── rag-expert/        # RAG 专家（Agent 对话）
└── components/
```

### 5.3 前后端交互

- **REST API**：常规 CRUD 操作
- **SSE (Server-Sent Events)**：Agent 流式输出
- **状态管理**：React Context + LocalStorage

---

## 6. 核心流程

### 6.1 艾宾浩斯复习调度

```
用户请求复习
    │
    ▼
ReviewService.get_next_question()
    │
    ├── 优先级1: 到期复习题 (next_review_time <= now)
    │
    ├── 优先级2: 当前轮次未刷题 (completed_in_current_round = false)
    │
    ├── 优先级3: 新题 (无学习记录)
    │
    └── 优先级4: 开启新轮次 (allow_new_round = true)
    │
    ▼
返回题目列表
    │
    ▼
用户提交答案
    │
    ▼
EbbinghausScheduler.calculate_next_review()
    │
    ├── 答对: stage + 1, 设置 next_review_time
    └── 答错: stage = 1, 设置 next_review_time
    │
    ▼
更新 UserLearningRecord
```

### 6.2 RAG 检索流程

```
用户提问 / Agent 请求
    │
    ▼
RAGService.retrieve()
    │
    ├── 解析 course.kb_version → 确定 Collection
    │
    ├── Retriever.vector_search() → Top-K 候选
    │
    ├── [可选] Reranker.rerank() → 重排序
    │
    └── [可选] HybridRetriever → 向量+关键词融合
    │
    ▼
返回 (content, metadata, score)
    │
    ▼
LLM Gateway 生成回答 (带 Langfuse 追踪)
    │
    ▼
返回答案 + 来源引用
```

### 6.3 Agent + SSE 流式执行

```
前端 EventSource 连接
    │
    ▼
API /api/agent/run
    │
    ▼
Agent.run(task_id, input_data)
    │
    ├── yield AgentEvent.agent_start()
    │
    ├── 调用 Skill (可能调用 RAG/LLM)
    │   │
    │   └── yield AgentEvent.skill_output()
    │
    ├── yield AgentEvent.token() (流式输出)
    │
    └── yield AgentEvent.agent_complete()
    │
    ▼
前端实时渲染
```

### 6.4 异步任务处理

```
API 请求 (导入/索引/评估)
    │
    ▼
enqueue_task(job_func, *args)
    │
    ▼
Redis Queue
    │
    ▼
Worker 进程执行
    │
    ├── 更新数据库
    ├── 写入向量存储
    └── 记录 Langfuse 追踪
    │
    ▼
API 轮询或回调获取结果
```

---

## 7. 架构决策记录

### ADR-001: 艾宾浩斯 9 阶段复习系统

**决策**：采用 9 阶段（0-8）的艾宾浩斯遗忘曲线实现，间隔从 30 分钟到 15 天。

**理由**：
- 科学依据的间隔重复算法
- 确定性阶段转换，易于测试和调试
- 阶段 8（已掌握）提供明确的学习完成状态

**影响**：
- 所有学习进度基于 `review_stage` 计算
- 题目推荐优先级依赖阶段和时间

### ADR-002: 课程级 RAG Collection + kb_version

**决策**：每个课程对应一个 ChromaDB Collection，通过 `kb_version` 管理版本。

**理由**：
- 避免 Collection 数量爆炸（相比章节级）
- 支持原子化版本切换
- 便于回滚和无缝更新

**影响**：
- Collection 命名：`course_{code}_{kb_version}`
- 查询时需先解析当前版本

### ADR-003: Skills 装饰器注册 + SSE 流式输出

**决策**：Agent 使用装饰器注册技能，执行过程通过 SSE 流式返回。

**理由**：
- 技能发现和解耦
- 长时间任务的用户体验
- 便于调试和监控

**影响**：
- Agent 方法使用 `@skill()` 装饰器
- API 返回 `StreamingResponse` (text/event-stream)

### ADR-004: 轮次制学习与艾宾浩斯解耦

**决策**：轮次管理和艾宾浩斯复习是两个独立系统。

**理由**：
- 轮次管理课程级别进度
- 艾宾浩斯管理题目级别记忆
- 两者独立演化，互不影响

**影响**：
- `completed_in_current_round` 与 `review_stage` 独立
- 新轮次不重置复习阶段

### ADR-005: Dev 模式边界绕过

**决策**：开发模式下通过 `user_id` 查询参数绕过认证。

**理由**：
- 加速本地开发迭代
- 不修改核心领域逻辑

**影响**：
- `DEV_MODE=true` 时启用
- 生产环境必须禁用

### ADR-006: LLM 边界可观测性

**决策**：所有 LLM 调用通过 `llm/` 模块并记录 Langfuse 追踪。

**理由**：
- LLM 行为难以预测，需要监控
- 支持成本分析和质量迭代

**影响**：
- 禁止直接调用 LLM API
- 使用 `trace_llm_call()` 装饰器

---

## 8. 扩展指南

### 8.1 添加新 API 端点

1. 在 `app/api/` 创建路由文件
2. 在 `app/services/` 创建或扩展服务
3. 在 `main.py` 注册路由

### 8.2 添加新数据模型

1. 在 `app/models/` 创建模型文件
2. 在 `app/models/__init__.py` 导入
3. 运行数据库迁移

### 8.3 添加新 Agent 技能

```python
from app.agent import Agent, skill

class MyAgent(Agent):
    @skill("my_skill", description="技能描述")
    def my_skill(self, param: str) -> dict:
        return {"result": "..."}
    
    async def execute(self, context):
        yield AgentEvent.agent_start()
        result = await self.call_skill("my_skill", param="...")
        yield AgentEvent.skill_output("my_skill", result)
        yield AgentEvent.agent_complete()
```

### 8.4 添加新 Embedding 模型

1. 在 `app/rag/embedding/models.py` 添加模型类
2. 在 `EMBEDDING_MODELS` 字典注册
3. 通过环境变量 `RAG_EMBEDDING_PROVIDER` 切换

### 8.5 架构不变量

⚠️ 以下规则必须保持：

1. **艾宾浩斯逻辑集中**：所有阶段计算在 `core/ebbinghaus.py`
2. **kb_version 选择器**：RAG 查询必须通过 `course.kb_version` 选择 Collection
3. **服务编排**：API 层不包含业务逻辑，只调用 Service
4. **LLM 边界**：所有 LLM 调用通过 `llm/` 模块
5. **异步任务**：耗时操作必须通过 Redis Queue

---

## 9. 术语表

| 术语 | 说明 |
|------|------|
| **review_stage** | 复习阶段（0-8），表示题目的记忆状态 |
| **kb_version** | 知识库版本号，用于 RAG Collection 版本管理 |
| **round** | 轮次，课程级别的学习进度单位 |
| **skill** | Agent 技能，通过装饰器注册的可调用方法 |
| **SSE** | Server-Sent Events，服务器推送事件，用于流式输出 |
| **Collection** | ChromaDB 中的向量集合，存储课程的 Chunk |
| **Chunk** | 文档分块，RAG 检索的基本单元 |
| **Langfuse** | LLM 监控平台，用于追踪和调试 LLM 调用 |

---

## 参考资料

- [README.md](./README.md) - 项目概述和快速开始
- [RAG_ARCHITECTURE.md](./RAG_ARCHITECTURE.md) - RAG 架构详细设计
- [PROJECT_HIGHLIGHTS.md](./PROJECT_HIGHLIGHTS.md) - 项目亮点总结
- [src/backend/README.md](./src/backend/README.md) - 后端开发文档
- [src/frontend/README.md](./src/frontend/README.md) - 前端开发文档

---

*最后更新: 2026-02-25*
