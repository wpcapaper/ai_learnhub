# RAG 知识库管理功能实现

**版本**: v1.0.1  
**日期**: 2026-02-20  
**类型**: 功能新增 + 架构修复

---

## 概述

本次更新为 Admin 端实现了完整的 RAG 知识库管理功能，包括章节级别的配置管理、文档块管理、召回测试等核心功能。

**架构修复 (v1.0.1)**:
- 移除了 `DocumentChunk` 模型，文档块数据完全存储在 ChromaDB
- 确保 Embedding 数据库与业务数据库完全解耦
- 业务数据库只存储 `ChapterKBConfig`（配置和状态）

---

## 架构设计

```
业务数据库 (SQLite/PostgreSQL)
└── ChapterKBConfig - 存储配置和索引状态

ChromaDB (data/chroma/)
└── chapter_{chapter_id} - 存储所有文档块和向量
    ├── 文档块内容 (documents)
    ├── 向量数据 (embeddings)
    └── 元数据 (metadata: source_file, content_type, is_active 等)
```

**设计原则**:
- Embedding 数据库与业务数据库完全解耦
- 知识库以 Chapter（章节）为维度，而非 Course
- 支持元数据回填（导入前生成 embedding，导入时回填 course_id/chapter_id）

---

## 新增功能

### 1. 数据模型

**模块路径**: `src/backend/app/models/`

| 模型 | 文件 | 说明 |
|------|------|------|
| ChapterKBConfig | `chapter_kb_config.py` | 章节知识库配置模型 |

**核心设计点**:
- 知识库以 Chapter（章节）为维度，而非 Course
- 支持元数据回填（导入前生成 embedding，导入时回填 course_id/chapter_id）
- 预留 GraphRAG 相关字段（实体、关系）
- **不存储文档块数据**（文档块存储在 ChromaDB）

### 2. ChromaVectorStore 增强

**模块路径**: `src/backend/app/rag/vector_store/chroma.py`

新增方法：
- `get_all_chunks()`: 获取集合中所有文档块（用于管理页面展示）

### 3. 知识库管理 API

**模块路径**: `src/backend/app/api/admin_kb.py`

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/admin/kb/status` | GET | 获取 RAG 系统状态（Embedding/Rerank 是否可用） |
| `/api/admin/kb/chapters/{id}/config` | GET/PUT | 章节知识库配置管理 |
| `/api/admin/kb/chapters/{id}/reindex` | POST | 重建章节索引（数据存入 ChromaDB） |
| `/api/admin/kb/chapters/{id}/chunks` | GET | 获取文档块列表（从 ChromaDB 读取） |
| `/api/admin/kb/chapters/{id}/test-retrieval` | POST | 召回测试 |
| `/api/admin/kb/backfill-metadata` | POST | 元数据回填 |

### 4. 代码块 LLM 摘要处理器

**模块路径**: `src/backend/app/rag/chunking/code_processor.py`

支持三种代码块处理策略：
- `preserve`: 保留原样
- `summarize`: 使用 LLM 生成摘要
- `hybrid`（推荐）: 短代码保留，长代码生成摘要

**关键特性**:
- 支持同步和异步处理
- 摘要失败时自动降级为保留原样
- 可配置摘要触发阈值（默认 500 字符）

### 5. 前端知识库管理页面

**模块路径**: `src/admin-frontend/app/knowledge-base/`

**页面功能**:
- 系统状态指示器（Embedding/Rerank 状态）
- 课程/章节选择器
- 文档块管理 Tab（列表、搜索、分页）
- 配置 Tab（切分策略、代码块处理、检索配置）
- 召回测试 Tab（查询测试、结果可视化）

---

## 配置变更

### 数据库新增表

```sql
-- 章节知识库配置表（仅存储配置，不存储文档块）
CREATE TABLE chapter_kb_configs (
    id VARCHAR(36) PRIMARY KEY,
    chapter_id VARCHAR(36),
    course_id VARCHAR(36),
    temp_ref VARCHAR(255),
    chunking_strategy VARCHAR(20) DEFAULT 'semantic',
    chunk_size INTEGER DEFAULT 1000,
    chunk_overlap INTEGER DEFAULT 200,
    code_block_strategy VARCHAR(20) DEFAULT 'hybrid',
    code_summary_threshold INTEGER DEFAULT 500,
    retrieval_mode VARCHAR(20) DEFAULT 'vector',
    -- GraphRAG 预留字段
    enable_graph_extraction BOOLEAN DEFAULT FALSE,
    graph_entity_types JSON,
    graph_relation_types JSON,
    -- 索引状态
    index_status VARCHAR(20) DEFAULT 'not_indexed',
    chunk_count INTEGER DEFAULT 0,
    indexed_at DATETIME,
    -- ...
);
```

**注意**: 文档块数据存储在 ChromaDB（`data/chroma/` 目录），不存储在业务数据库。

---

## 文件变更清单

### 后端新增文件

```
src/backend/app/models/
└── chapter_kb_config.py      # 章节知识库配置模型

src/backend/app/api/
└── admin_kb.py                # 知识库管理 API

src/backend/app/rag/chunking/
└── code_processor.py          # 代码块 LLM 摘要处理器
```

### 后端修改文件

```
src/backend/app/models/__init__.py     # 导出新模型
src/backend/main.py                    # 注册新路由
src/backend/app/rag/chunking/__init__.py  # 导出 code_processor
src/backend/app/rag/vector_store/chroma.py  # 新增 get_all_chunks 方法
```

### 前端新增文件

```
src/admin-frontend/app/knowledge-base/
└── page.tsx                   # 知识库管理页面

src/admin-frontend/lib/
└── api.ts                     # 新增知识库管理 API 方法和类型
```

---

## 使用说明

### 1. 检查系统状态

访问 `/knowledge-base` 页面，系统会自动检测 Embedding 和 Rerank 状态。

### 2. 配置章节知识库

1. 选择课程和章节
2. 切换到"配置" Tab
3. 设置切分策略、代码块处理方式、检索模式
4. 点击"保存配置"

### 3. 建立索引

1. 配置完成后，点击"重建索引"
2. 系统会根据配置切分文档并生成向量（存储到 ChromaDB）

### 4. 测试召回

1. 切换到"召回测试" Tab
2. 输入测试查询
3. 查看返回结果和相似度

### 5. 应用数据库迁移

运行以下命令创建新表：
```bash
cd scripts
uv run python init_db.py
```

---

## 后续计划

- [ ] 集成 shadcn 和 magic_ui 组件增强 UI
- [ ] 实现 GraphRAG 实体提取
- [ ] 添加批量测试和测试报告导出
- [ ] 实现元数据自动回填到向量库

---

## 相关文档

- 设计文档: [change_intent/rag_knowledge_base_management.md](../change_intent/rag_knowledge_base_management.md)
- RAG 模块文档: [src/backend/app/rag/README.md](../src/backend/app/rag/README.md)
