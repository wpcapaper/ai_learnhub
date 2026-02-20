# RAG系统使用手册

AILearn Hub的RAG（检索增强生成）系统为AI助教提供课程内容检索能力。

---

## 目录

- [快速启用](#快速启用)
- [配置说明](#配置说明)
- [本地Embedding服务](#本地embedding服务)
- [Admin管理后台](#admin管理后台)
- [API使用](#api使用)
- [常见问题](#常见问题)

---

## 端口说明

端口可通过项目根目录的 `.env` 文件配置（复制 `.env.example`）。

| 服务 | 默认端口 | 访问地址 | 说明 |
|------|----------|----------|------|
| Backend API | 8000 | http://localhost:8000 | 核心业务 API |
| Frontend (C端) | 3000 | http://localhost:3000 | 用户端前端 |
| Admin Frontend | 8080 | http://localhost:8080 | 管理端前端 |
| Langfuse | 9090 | http://localhost:9090 | LLM 监控平台 |

**配置方式**：

```bash
# 复制配置文件
cp .env.example .env

# 修改端口（可选）
BACKEND_PORT=8000
FRONTEND_PORT=3000
ADMIN_FRONTEND_PORT=8080
LANGFUSE_PORT=9090
```

---

## 快速启用

### 依赖已内置

RAG依赖已在 `pyproject.toml` 中配置，无需额外安装：

```bash
cd src/backend
uv sync
```

### 最简配置

RAG模块**根据配置自动启用**，未配置时不影响主服务。

只需设置一个环境变量：

```bash
# 使用OpenAI（推荐）
export RAG_OPENAI_API_KEY=sk-your-key-here

# 或使用本地Ollama
export RAG_EMBEDDING_PROVIDER=local
export RAG_EMBEDDING_SERVICE_URL=http://localhost:11434/api/embeddings
```

### 验证状态

```bash
curl http://localhost:8000/health

# 已启用
{"status": "healthy", "rag_available": true, "admin_available": true}

# 未启用（缺少配置）
{"status": "healthy", "rag_available": false, "admin_available": true}
```

---

## 配置说明

### 环境变量

所有RAG相关变量使用 `RAG_` 前缀，与项目其他LLM用途区分：

**Embedding配置：**

| 变量名 | 必需 | 说明 | 默认值 |
|--------|------|------|--------|
| `RAG_EMBEDDING_PROVIDER` | 否 | 提供商：openai / local / custom | `openai` |
| `RAG_OPENAI_API_KEY` | openai模式必需 | OpenAI API密钥 | - |
| `RAG_OPENAI_BASE_URL` | 否 | OpenAI兼容服务地址 | `https://api.openai.com/v1` |
| `RAG_EMBEDDING_MODEL` | 否 | 模型名称 | `text-embedding-3-small` |
| `RAG_EMBEDDING_SERVICE_URL` | local模式必需 | 本地服务地址 | - |
| `RAG_EMBEDDING_LOCAL_MODEL` | 否 | 本地模型名 | `nomic-embed-text` |

**检索策略配置：**

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `RAG_RETRIEVAL_MODE` | 检索模式：vector / vector_rerank / hybrid | `vector` |

**Rerank配置（可选）：**

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `RAG_RERANK_ENABLED` | 是否启用Rerank | `false` |
| `RAG_RERANK_PROVIDER` | 提供商：local / cohere | `local` |
| `RAG_RERANK_SERVICE_URL` | 本地Rerank服务地址 | - |
| `RAG_RERANK_COHERE_API_KEY` | Cohere API密钥 | - |

### 检索模式说明

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `vector` | 纯向量检索 | 默认模式，最简单 |
| `vector_rerank` | 向量检索 + Rerank重排序 | 需要更高精确度 |
| `hybrid` | 混合检索（向量+关键词） | 专业搜索场景 |

### 配置示例

**使用OpenAI：**

```bash
# src/backend/.env
RAG_OPENAI_API_KEY=sk-xxx
RAG_OPENAI_BASE_URL=https://api.openai.com/v1
```

**使用DeepSeek等兼容服务：**

```bash
RAG_OPENAI_API_KEY=sk-xxx
RAG_OPENAI_BASE_URL=https://api.deepseek.com/v1
```

**使用本地Ollama：**

```bash
RAG_EMBEDDING_PROVIDER=local
RAG_EMBEDDING_SERVICE_URL=http://localhost:11434/api/embeddings
RAG_EMBEDDING_LOCAL_MODEL=nomic-embed-text
```

### 配置文件

`src/backend/config/rag_config.yaml` 支持通过环境变量覆盖：

```yaml
embedding:
  provider: "${RAG_EMBEDDING_PROVIDER:openai}"
  openai:
    model: "${RAG_EMBEDDING_MODEL:text-embedding-3-small}"
    api_key: "${RAG_OPENAI_API_KEY:}"
  local:
    endpoint: "${RAG_EMBEDDING_SERVICE_URL:http://localhost:11434/api/embeddings}"
    model: "${RAG_EMBEDDING_LOCAL_MODEL:nomic-embed-text}"

rerank:
  enabled: "${RAG_RERANK_ENABLED:false}"
  provider: "${RAG_RERANK_PROVIDER:local}"
  local:
    endpoint: "${RAG_RERANK_SERVICE_URL:http://localhost:8002/rerank}"

vector_store:
  type: "chroma"
  persist_directory: "./data/chroma"

retrieval:
  default_top_k: 5
  mode: "${RAG_RETRIEVAL_MODE:vector}"
  vector_weight: 0.7
  keyword_weight: 0.3
```

### 智能降级

系统支持自动降级，无需担心配置缺失：

| 配置模式 | 缺失组件 | 降级行为 |
|----------|----------|----------|
| `vector_rerank` | Rerank服务 | 自动降级为 `vector` |
| `hybrid` | 关键词检索 | 自动降级为 `vector` |

---

## Rerank（可选）

Rerank用于对检索结果进行二次重排序，提升精确度。

### 工作原理

```
用户查询 → 向量检索(Top 20) → Rerank重排序 → 返回(Top 5)
```

### 为什么Rerank与Embedding分开？

1. **Ollama对rerank模型支持有限** - 不建议用Ollama做rerank
2. **模型差异大** - rerank需要专门的交叉编码器模型
3. **可独立部署** - rerank服务可单独扩展

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `RAG_RERANK_ENABLED` | 是否启用 | `false` |
| `RAG_RERANK_PROVIDER` | 提供商：local / cohere | `local` |
| `RAG_RERANK_SERVICE_URL` | 本地rerank服务地址 | `http://localhost:8002/rerank` |
| `RAG_RERANK_COHERE_API_KEY` | Cohere API密钥 | - |
| `RAG_RERANK_MODEL` | 模型名称 | `rerank-multilingual` |

### 方案一：Cohere API（推荐）

```bash
export RAG_RERANK_ENABLED=true
export RAG_RERANK_PROVIDER=cohere
export RAG_RERANK_COHERE_API_KEY=your-cohere-key
```

### 方案二：自建Rerank服务

使用 `bge-reranker` 等模型搭建独立服务：

```bash
# 启用rerank
export RAG_RERANK_ENABLED=true
export RAG_RERANK_SERVICE_URL=http://localhost:8002/rerank
```

Rerank服务需要实现：

```python
# POST {endpoint}
# Request
{
  "query": "用户查询",
  "documents": [
    {"id": "chunk_1", "text": "文档内容1"},
    {"id": "chunk_2", "text": "文档内容2"}
  ]
}
# Response
{
  "results": [
    {"id": "chunk_2", "score": 0.95},
    {"id": "chunk_1", "score": 0.72}
  ]
}
```

### 推荐Rerank模型

| 模型 | 语言 | 部署方式 |
|------|------|----------|
| `bge-reranker-large` | 中文 | 自建服务 |
| `bge-reranker-v2-m3` | 多语言 | 自建服务 |
| `cohere-rerank` | 多语言 | API调用 |

---

## 本地Embedding服务

### 使用Ollama

```bash
# 1. 安装Ollama
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# 2. 启动服务
ollama serve

# 3. 下载Embedding模型
ollama pull nomic-embed-text

# 4. 配置并启动后端
export RAG_EMBEDDING_PROVIDER=local
export RAG_EMBEDDING_SERVICE_URL=http://localhost:11434/api/embeddings
export RAG_EMBEDDING_LOCAL_MODEL=nomic-embed-text

cd src/backend
uv run uvicorn main:app --reload
```

### 其他本地服务

任何HTTP API服务均可，需实现：

```python
# POST {endpoint}
# Request (Ollama格式)
{"model": "model-name", "input": ["文本1", "文本2"]}
# Response
{"embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]]}
```

---

## Admin管理后台

### 启动

```bash
cd src/admin-frontend
npm install
npm run dev
```

访问 **http://localhost:3002**

### 页面功能

| 页面 | 路径 | 功能 |
|------|------|------|
| 课程管理 | `/` | 转换课程、查看质量报告 |
| RAG专家 | `/rag-expert` | CLI风格交互 |
| RAG测试 | `/rag-test` | 召回测试 |
| 分块优化 | `/optimization` | 策略对比 |

---

## API使用

### 索引内容

```bash
curl -X POST http://localhost:8000/api/rag/index \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# 课程内容...",
    "course_id": "python_basics",
    "clear_existing": true
  }'
```

### 检索

```bash
curl -X POST http://localhost:8000/api/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是变量？",
    "course_id": "python_basics",
    "top_k": 5
  }'
```

### 查看索引状态

```bash
curl http://localhost:8000/api/rag/collection/python_basics/size
```

---

## 常见问题

### Q: rag_available 显示 false？

**原因**：缺少必要配置

**解决**：设置 `RAG_OPENAI_API_KEY` 或配置本地服务

### Q: Ollama调用失败？

**检查**：
1. 服务是否启动：`ollama serve`
2. 模型是否下载：`ollama list`
3. 地址是否正确：默认 `http://localhost:11434`

### Q: 如何重置RAG数据？

```bash
rm -rf src/backend/data/chroma/
```

### Q: 如何切换Embedding模型？

1. 修改环境变量
2. 删除现有向量数据（维度可能不同）
3. 重启服务

---

## 相关文档

- [变更日志](./change_log/rag_integration.md)
- [课程导入指南](./COURSE_IMPORT_GUIDE.md)
- [环境变量示例](./src/backend/.env.example)
