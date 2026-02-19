# RAG系统与课程管理集成

**版本**: v1.0.0  
**日期**: 2026-02-19  
**类型**: 功能新增

---

## 概述

本次更新为AILearn Hub集成了完整的RAG（检索增强生成）系统和课程管理功能，为AI助教提供基于课程内容的智能检索能力。

---

## 新增功能

### 1. 课程转换管道

**模块路径**: `src/backend/app/course_pipeline/`

| 功能 | 说明 |
|------|------|
| 多格式支持 | 支持 Markdown (.md) 和 Jupyter Notebook (.ipynb) |
| 章节自动排序 | 智能识别数字/中文/英文等多种命名模式 |
| 代码块处理 | ipynb代码单元格保留执行结果说明 |
| 格式规范化 | 自动清理Markdown格式问题 |

**新增文件**:
- `course_pipeline/models.py` - 数据模型定义
- `course_pipeline/pipeline.py` - 主转换管道
- `course_pipeline/converters/__init__.py` - 格式转换器
- `course_pipeline/evaluators/__init__.py` - 质量评估器

### 2. 课程质量评估Agent

**功能**: 自动检测课程内容中的问题和改进空间

| 检查维度 | 说明 |
|----------|------|
| 内容完整性 | 空章节、过短章节、TODO标记 |
| 逻辑一致性 | 术语定义冲突 |
| 准确性检查 | 版本说明缺失、代码块语言标记 |
| 争议识别 | 绝对化表述、个人观点 |
| 格式规范 | 标题层级跳跃、未闭合代码块 |

**输出**: `courses/{course_id}/quality_report.json`

### 3. RAG模块（弱依赖）

**模块路径**: `src/backend/app/rag/`

| 组件 | 说明 |
|------|------|
| Embedding | 支持OpenAI/本地服务/自定义服务 |
| 向量存储 | ChromaDB（独立于业务数据库） |
| 分块策略 | 语义分块、固定分块、标题分块 |
| 召回测试 | 支持批量测试和指标计算 |

**数据独立性**:
```
app.db              ← 业务数据（用户、题目）
data/chroma/        ← RAG向量数据（完全独立）
```

### 4. Admin管理前端

**项目路径**: `src/admin-frontend/`

**访问地址**: http://localhost:3002（避免与C端前端3000端口冲突）

独立的前端项目，包含：

| 页面 | 路径 | 功能 |
|------|------|------|
| 课程管理 | `/` | 转换课程、查看质量报告 |
| RAG专家 | `/rag-expert` | CLI风格交互界面 |
| RAG测试 | `/rag-test` | 可视化召回测试 |
| 分块优化 | `/optimization` | 策略对比分析 |

### 5. 自适应RAG分块优化

**功能**: 自动测试多种分块策略，推荐最佳配置

支持的策略：
- `semantic_small` - 小型语义块（100-500字符）
- `semantic_medium` - 中型语义块（200-1000字符）
- `semantic_large` - 大型语义块（500-2000字符）
- `fixed_small` - 固定256字符
- `fixed_medium` - 固定512字符
- `heading_based` - 按标题分割

### 6. 管理端API

**新增端点**: `/api/admin/*`

| 端点 | 方法 | 功能 |
|------|------|------|
| `/admin/courses` | GET | 课程列表 |
| `/admin/courses/convert` | POST | 触发转换 |
| `/admin/quality/{id}` | GET | 质量报告 |
| `/admin/rag/optimize` | POST | 运行优化 |
| `/admin/rag/config` | GET/PUT | 配置管理 |

---

## 配置变更

### 新增配置文件

**文件**: `src/backend/config/rag_config.yaml`

```yaml
embedding:
  provider: "${RAG_EMBEDDING_PROVIDER:openai}"
  openai:
    model: "${RAG_EMBEDDING_MODEL:text-embedding-3-small}"
    api_key: "${RAG_OPENAI_API_KEY:}"
    base_url: "${RAG_OPENAI_BASE_URL:https://api.openai.com/v1}"
  local:
    endpoint: "${RAG_EMBEDDING_SERVICE_URL:http://localhost:11434/api/embeddings}"
    model: "${RAG_EMBEDDING_LOCAL_MODEL:nomic-embed-text}"

vector_store:
  type: "chroma"
  persist_directory: "./data/chroma"
```

### 新增环境变量

所有RAG相关变量使用 `RAG_` 前缀，与项目其他LLM用途区分：

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `RAG_EMBEDDING_PROVIDER` | 否 | 提供商（openai/local/custom） |
| `RAG_OPENAI_API_KEY` | OpenAI模式必需 | API密钥 |
| `RAG_OPENAI_BASE_URL` | 否 | 兼容服务地址 |
| `RAG_EMBEDDING_SERVICE_URL` | 本地模式必需 | 本地服务地址（Ollama等） |
| `RAG_EMBEDDING_ENDPOINT` | 自定义模式必需 | 自定义服务地址 |

### Docker配置更新

**文件**: `docker-compose.yml`

新增 `admin-frontend` 服务（可选启动）：

```bash
# 生产模式
docker-compose --profile admin up

# 开发模式（本地npm）
cd src/admin-frontend && npm run dev
```

**新增文件**:
- `src/admin-frontend/Dockerfile` - 生产构建镜像
- `src/admin-frontend/.dockerignore` - Docker构建排除

---

## 依赖变更

### Python依赖（已内置）

RAG依赖已添加到 `pyproject.toml`，无需单独安装：

```toml
[project.dependencies]
chromadb = ">=0.4.0"
httpx = ">=0.25.0"
numpy = ">=1.24.0"
langdetect = ">=1.0.9"
pyyaml = ">=6.0.0"
```

**注意**：不包含模型文件，所有Embedding通过HTTP API调用。

### Node.js依赖（admin-frontend）

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "marked": "^15.0.0",
    "highlight.js": "^11.10.0"
  }
}
```

---

## .gitignore更新

新增忽略规则：

```gitignore
# ChromaDB向量数据库（独立存储）
src/backend/data/chroma/
**/chroma/

# RAG优化报告
**/rag_optimization_report.json
```

---

## 后端代码变更

### main.py

- 新增Admin模块弱加载支持
- 健康检查返回 `admin_available` 状态

### 新增API模块

- `app/api/admin.py` - 管理端API路由

---

## 架构说明

### 数据存储分离

```
┌─────────────────────────────────────────────┐
│                  AILearn Hub                │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐    ┌─────────────────────┐│
│  │  app.db     │    │  data/chroma/       ││
│  │  业务数据    │    │  RAG向量数据         ││
│  │  用户/题目   │    │  完全独立            ││
│  └─────────────┘    └─────────────────────┘│
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │  courses/{course_id}/                   ││
│  │  ├── course.json          课程元数据     ││
│  │  ├── *.md                 章节文件       ││
│  │  ├── quality_report.json  质量报告       ││
│  │  └── rag_optimization_report.json       ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

### 模块弱加载

RAG和Admin模块采用弱依赖设计：
- 依赖缺失时不影响主服务运行
- 健康检查返回模块可用状态
- 相关API在模块不可用时返回错误

### 检索策略可配置

支持三种检索模式，通过 `RAG_RETRIEVAL_MODE` 环境变量配置：

| 模式 | 说明 | 配置要求 |
|------|------|----------|
| `vector` | 纯向量检索（默认） | 仅需Embedding配置 |
| `vector_rerank` | 向量+Rerank重排序 | 需额外配置Rerank服务 |
| `hybrid` | 混合检索（向量+关键词） | 需额外配置关键词检索 |

**智能降级机制**：
- Rerank未配置时，`vector_rerank` 自动降级为 `vector`
- 关键词检索未配置时，`hybrid` 自动降级为 `vector`

### Rerank与Embedding独立配置

由于Ollama对Rerank模型支持有限，Rerank服务与Embedding服务完全独立：

```
Embedding服务                    Rerank服务
    ↓                               ↓
Ollama (nomic-embed-text)    bge-reranker / Cohere API
http://localhost:11434        http://localhost:8002
```

### LLM统一封装

新增同步接口，适用于后台任务场景：

```python
from app.llm import get_llm_client

llm = get_llm_client()

# 异步调用（API请求）
response = await llm.chat(messages, temperature=0.7)

# 同步调用（后台任务）
response = llm.chat_sync(messages, temperature=0.3)
```

### 提示词模板化

质量评估Agent的提示词已迁移到YAML模板：

**新增文件**: `prompts/templates/course_quality_evaluator.yaml`

```
prompts/templates/
├── ai_assistant.yaml              # AI助教提示词
└── course_quality_evaluator.yaml  # 课程质量评估提示词
```

使用方式：
```python
from app.prompts.loader import prompt_loader

messages = prompt_loader.get_messages("course_quality_evaluator", 
    course_title="Python基础",
    course_content="..."
)
```

---

## 使用文档

详见 [RAG_MANUAL.md](../RAG_MANUAL.md)

---

## 后续计划

- [ ] 与AI助教Agent联调
- [ ] GraphRAG支持（利用知识图谱）
- [ ] 更多Embedding模型支持
- [ ] 管理端访问控制增强

---

## 相关Issue/PR

- 设计文档: [change_intent/prompt_rag_plan.md](../change_intent/prompt_rag_plan.md)
