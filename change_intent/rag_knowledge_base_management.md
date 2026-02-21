# RAG 知识库管理功能实现计划

**版本**: v1.0  
**日期**: 2026-02-20  
**状态**: 规划中

---

## 一、需求概述

### 1.1 核心目标

在 Admin 端实现完整的 RAG 知识库管理功能，包括：
1. **文档分割策略配置** - 支持默认策略和手动配置
2. **知识库文档块管理** - 类似 Dify 的可视化块管理页面
3. **召回测试** - 增强现有测试页面

### 1.2 关键约束

| 约束项 | 说明 |
|--------|------|
| Embedding 配置 | 使用本地 Ollama 部署的 bge-m3 模型 |
| Rerank | 暂未配置，功能可选 |
| 配置维度 | 检索模式等配置应跟随知识库，而非全局系统变量 |
| 注释要求 | 所有关键业务逻辑必须有中文注释 |
| 文档格式 | 主要为 Markdown，包括 ipynb 转换的 |

### 1.3 特殊需求：代码块处理

课程中存在 ipynb 转换的 Markdown，代码块处理策略：
- **采用混合策略**：
  - 短代码（<500字符）：保留原样
  - 长代码（>=500字符）：使用 LLM 生成摘要 + 原代码作为附件存储

### 1.4 关键架构决策

| 决策点 | 说明 |
|--------|------|
| **知识库维度** | 以 Chapter（章节）为维度，而非整个 Course。一个 Chapter 可能有多个 Document |
| **GraphRAG 预留** | 数据模型预埋知识图谱相关字段，为后续图检索做准备 |
| **元数据回填机制** | Embedding 可在导入前生成，导入系统时回填 course_id/chapter_id |
| **模型状态检测** | 页面需检测 Embedding/Rerank 模型是否就绪，无 Embedding 时功能禁用 |
| **后续扩展** | 预留问答对生成能力，用于提升召回效果 |

---

## 二、架构设计

### 2.1 配置层级重构

**问题**: 当前 `RAG_RETRIEVAL_MODE` 等是全局环境变量，不适合多知识库场景。

**解决方案**: 配置分为三层：

```
┌─────────────────────────────────────────────────────────┐
│                    全局默认配置                          │
│  (rag_config.yaml / 环境变量)                           │
│  - embedding provider (全局唯一)                        │
│  - rerank 配置 (全局唯一)                               │
│  - 默认切分策略参数                                     │
│  - 默认检索模式                                         │
└─────────────────────────────────────────────────────────┘
                          ↓ 可被覆盖
┌─────────────────────────────────────────────────────────┐
│                   知识库级配置                           │
│  (数据库 knowledge_base_configs 表)                     │
│  - 切分策略类型 (semantic/fixed/heading)                │
│  - 切分参数 (chunk_size, overlap 等)                    │
│  - 检索模式 (vector/hybrid)                             │
│  - 代码块处理策略                                       │
│  - Top-K 值                                             │
└─────────────────────────────────────────────────────────┘
                          ↓ 可被覆盖
┌─────────────────────────────────────────────────────────┐
│                   单次查询配置                           │
│  (API 请求参数)                                         │
│  - top_k                                                │
│  - score_threshold                                      │
│  - filters                                              │
└─────────────────────────────────────────────────────────┘
```

### 2.2 新增数据模型

```sql
-- 章节知识库配置表（以 Chapter 为维度）
CREATE TABLE chapter_kb_configs (
    id VARCHAR(36) PRIMARY KEY,
    chapter_id VARCHAR(36),  -- 可为空（导入前生成embedding的情况）
    course_id VARCHAR(36),   -- 可为空（导入前生成embedding的情况）
    
    -- 临时标识符（导入前使用）
    temp_ref VARCHAR(255),   -- 如文件路径，用于匹配回填
    
    -- 切分策略配置
    chunking_strategy VARCHAR(20) DEFAULT 'semantic',  -- semantic/fixed/heading
    chunk_size INTEGER DEFAULT 1000,
    chunk_overlap INTEGER DEFAULT 200,
    min_chunk_size INTEGER DEFAULT 100,
    
    -- 代码块处理
    code_block_strategy VARCHAR(20) DEFAULT 'hybrid',  -- preserve/summarize/hybrid
    code_summary_threshold INTEGER DEFAULT 500,  -- 字符数阈值
    
    -- 检索配置
    retrieval_mode VARCHAR(20) DEFAULT 'vector',  -- vector/hybrid/vector_rerank/graph
    default_top_k INTEGER DEFAULT 5,
    score_threshold FLOAT DEFAULT 0.0,
    
    -- GraphRAG 预留字段
    enable_graph_extraction BOOLEAN DEFAULT FALSE,  -- 是否启用知识图谱提取
    graph_entity_types JSON,  -- 实体类型配置 ["概念", "方法", "工具"]
    graph_relation_types JSON,  -- 关系类型配置 ["包含", "依赖", "等价"]
    
    -- 索引状态
    indexed_at TIMESTAMP,
    chunk_count INTEGER DEFAULT 0,
    graph_entity_count INTEGER DEFAULT 0,  -- 知识图谱实体数量
    graph_relation_count INTEGER DEFAULT 0,  -- 知识图谱关系数量
    index_status VARCHAR(20) DEFAULT 'not_indexed',  -- not_indexed/indexing/indexed/failed
    
    -- 元数据回填状态
    metadata_backfilled BOOLEAN DEFAULT FALSE,  -- course_id/chapter_id 是否已回填
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- 唯一约束：chapter_id 或 temp_ref 必须有值
    CONSTRAINT chk_ref CHECK (chapter_id IS NOT NULL OR temp_ref IS NOT NULL)
);

-- 文档块表（用于管理和展示）
CREATE TABLE document_chunks (
    id VARCHAR(36) PRIMARY KEY,
    kb_config_id VARCHAR(36) NOT NULL,  -- 关联章节知识库配置
    
    -- 元数据（可回填）
    course_id VARCHAR(36),   -- 可为空，导入时回填
    chapter_id VARCHAR(36),  -- 可为空，导入时回填
    
    -- 内容
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',  -- text/code/summary/qa_pair
    
    -- 如果是代码块摘要
    original_code TEXT,  -- 原始代码（如果 content 是摘要）
    
    -- 来源信息
    source_file VARCHAR(255),
    position INTEGER,
    char_count INTEGER,
    
    -- GraphRAG 预留
    entities JSON,  -- 提取的实体 [{"name": "Transformer", "type": "概念"}]
    relations JSON,  -- 提取的关系 [{"from": "Transformer", "to": "Encoder", "type": "包含"}]
    
    -- 向量信息
    vector_id VARCHAR(100),  -- ChromaDB 中的 ID
    indexed_at TIMESTAMP,
    
    -- 管理状态
    is_active BOOLEAN DEFAULT TRUE,
    manual_edit BOOLEAN DEFAULT FALSE,  -- 是否手动编辑过
    
    -- 元数据回填状态
    metadata_backfilled BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    
    FOREIGN KEY (kb_config_id) REFERENCES chapter_kb_configs(id)
);

-- 知识图谱实体表（GraphRAG 预留）
CREATE TABLE graph_entities (
    id VARCHAR(36) PRIMARY KEY,
    kb_config_id VARCHAR(36) NOT NULL,
    
    name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- 概念/方法/工具/人物
    
    -- 描述
    description TEXT,
    
    -- 来源
    source_chunk_ids JSON,  -- 来自哪些文档块
    
    -- 向量（用于语义检索）
    vector_id VARCHAR(100),
    
    -- 元数据
    properties JSON,  -- 额外属性
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (kb_config_id) REFERENCES chapter_kb_configs(id)
);

-- 知识图谱关系表（GraphRAG 预留）
CREATE TABLE graph_relations (
    id VARCHAR(36) PRIMARY KEY,
    kb_config_id VARCHAR(36) NOT NULL,
    
    from_entity_id VARCHAR(36) NOT NULL,
    to_entity_id VARCHAR(36) NOT NULL,
    relation_type VARCHAR(50) NOT NULL,  -- 包含/依赖/等价/对比
    
    -- 证据
    evidence TEXT,  -- 原文中支持该关系的文本
    source_chunk_id VARCHAR(36),
    
    -- 置信度
    confidence FLOAT DEFAULT 1.0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (kb_config_id) REFERENCES chapter_kb_configs(id),
    FOREIGN KEY (from_entity_id) REFERENCES graph_entities(id),
    FOREIGN KEY (to_entity_id) REFERENCES graph_entities(id)
);
```

### 2.3 Markdown 切分策略优化

针对 Markdown 文档的智能切分：

```python
class MarkdownChunkingStrategy:
    """Markdown 专用切分策略"""
    
    def __init__(self, config: KnowledgeBaseConfig):
        self.config = config
    
    def chunk(self, content: str, ...) -> List[Chunk]:
        """
        切分逻辑：
        1. 按标题层级切分（H1-H6）
        2. 保持代码块完整性
        3. 处理列表、表格等结构
        4. 应用代码块处理策略
        """
        pass
```

**切分规则**：

| 元素类型 | 处理方式 |
|----------|----------|
| 标题 (H1-H6) | 作为切分边界，保留在块开头 |
| 代码块 | 根据策略：保留原样/生成摘要/混合 |
| 列表 | 整体保留，不跨块切分 |
| 表格 | 整体保留 |
| 普通段落 | 按语义边界切分 |
| 图片链接 | 替换为 [图片: alt] 占位符 |

### 2.4 代码块处理策略

```python
class CodeBlockProcessor:
    """代码块处理器"""
    
    def process(self, code: str, language: str, strategy: str) -> ProcessedCode:
        """
        处理策略：
        - preserve: 保留原样
        - summarize: 调用 LLM 生成摘要
        - hybrid: 长代码生成摘要，短代码保留
        """
        pass
```

---

## 三、API 设计

### 3.0 系统状态 API

```yaml
# GET /api/admin/rag/status
# 获取 RAG 系统状态（Embedding/Rerank 是否可用）
Response:
  embedding:
    available: boolean
    provider: string  # openai/local/custom
    model: string
    message: string
  rerank:
    available: boolean
    provider: string
    model: string
    message: string
  ready: boolean  # embedding 可用时为 true
```

### 3.1 章节知识库配置 API

```yaml
# GET /api/admin/chapters/{chapter_id}/kb-config
# 获取章节知识库配置
Response:
  config:
    chunking_strategy: string
    chunk_size: number
    code_block_strategy: string
    retrieval_mode: string
    enable_graph_extraction: boolean
    # ...
  stats:
    chunk_count: number
    graph_entity_count: number
    index_status: string
    metadata_backfilled: boolean

# PUT /api/admin/chapters/{chapter_id}/kb-config
# 更新章节知识库配置
Request:
  chunking_strategy: string
  chunk_size: number
  code_block_strategy: string
  retrieval_mode: string
  enable_graph_extraction: boolean
  # ...

# POST /api/admin/chapters/{chapter_id}/reindex
# 重建章节索引
Request:
  clear_existing: boolean
Response:
  task_id: string
  status: string

# POST /api/admin/chapters/backfill-metadata
# 批量回填元数据（导入课程时调用）
Request:
  course_id: string
  chapters:
    - chapter_id: string
      temp_ref: string  # 文件路径
Response:
  backfilled_count: number
```

### 3.2 文档块管理 API

```yaml
# GET /api/admin/chapters/{chapter_id}/chunks
# 获取章节的文档块列表（分页）
Request:
  page: number
  page_size: number
  content_type: string  # 可选过滤
  search: string  # 可选搜索
Response:
  chunks:
    - id: string
      content: string
      content_type: string
      source_file: string
      char_count: number
      is_active: boolean
      entities: array  # GraphRAG 实体
  total: number
  page: number
  page_size: number

# GET /api/admin/chunks/{chunk_id}
# 获取单个文档块详情
Response:
  chunk:
    id: string
    content: string
    content_type: string
    original_code: string  # 如果是摘要
    source_file: string
    metadata: object
    entities: array
    relations: array

# PUT /api/admin/chunks/{chunk_id}
# 更新文档块（手动编辑）
Request:
  content: string
  is_active: boolean

# DELETE /api/admin/chunks/{chunk_id}
# 删除文档块

# POST /api/admin/chunks/{chunk_id}/reactivate
# 重新激活已删除的块
```

### 3.3 召回测试 API（增强）

```yaml
# POST /api/admin/chapters/{chapter_id}/test-retrieval
# 召回测试（支持临时参数）
Request:
  query: string
  top_k: number
  retrieval_mode: string  # 可临时覆盖
  score_threshold: number
Response:
  results:
    - chunk_id: string
      content: string
      score: number
      source: string
  query_time_ms: number

# POST /api/admin/chapters/{chapter_id}/batch-test
# 批量召回测试
Request:
  test_cases:
    - query: string
      expected_chunks: string[]  # 期望命中的块ID
Response:
  results:
    - query: string
      hits: number
      recall: number
      precision: number
  overall_metrics:
    avg_recall: number
    avg_precision: number
    mrr: number
```

---

## 四、前端页面设计

### 4.0 系统状态组件（全局）

**位置**: 页面顶部或侧边栏

**功能**:
- 显示 Embedding 状态：🟢 已就绪 / 🔴 不可用
- 显示 Rerank 状态：🟢 已就绪 / 🟡 未配置 / 🔴 不可用
- 无 Embedding 时：禁用所有 RAG 功能，显示配置引导

```tsx
<RAGStatusIndicator>
  {embeddingAvailable ? (
    <Badge variant="success">
      <AnimatedGradientText>Embedding 已就绪</AnimatedGradientText>
      <span className="text-xs">{provider} / {model}</span>
    </Badge>
  ) : (
    <Badge variant="destructive">
      Embedding 不可用 - 请检查配置
    </Badge>
  )}
</RAGStatusIndicator>
```

### 4.1 章节知识库管理页面（新建）

**路径**: `/courses/{courseId}/chapters/{chapterId}/knowledge-base`

**功能**:
- 显示章节知识库状态
- 配置切分策略
- 管理文档块
- 测试召回

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  [状态栏] Embedding: 🟢 已就绪 | Rerank: 🟡 未配置         │
├─────────────────────────────────────────────────────────────┤
│  章节: 第一章 大语言模型概述                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 文档块      │  │ 索引状态    │  │ 知识图谱    │         │
│  │ 128 个      │  │ 已索引      │  │ 45 实体     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  [Tab: 文档块] [Tab: 配置] [Tab: 召回测试] [Tab: 知识图谱]  │
├─────────────────────────────────────────────────────────────┤
│  (各 Tab 内容)                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 文档块管理 Tab

**布局**:
```
┌─────────────────────────────────────────────────────────────┐
│  [搜索框]  [类型过滤▼]  [状态过滤▼]        [重建索引]      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │ #1 介绍                                  文本 | 1,234字  ││
│  │ 大语言模型（LLM）是一种基于深度学习的...                 ││
│  │ 来源: 01_introduction.md                [编辑] [禁用]   ││
│  │ 实体: Transformer, Encoder, Decoder                     ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ #2 Transformer 实现                   代码摘要 | 156字  ││
│  │ [摘要] 实现了一个基础的Transformer编码器，包含多头...   ││
│  │ [查看原代码]                            [编辑] [禁用]   ││
│  └─────────────────────────────────────────────────────────┘│
│  ...                                                        │
│  [上一页] 1 2 3 ... 10 [下一页]                            │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 配置 Tab

**配置项**:

```yaml
切分策略配置:
  - 策略类型: [语义切分 | 固定大小 | 按标题]
  - 最大块大小: 滑块 (200-2000)
  - 重叠大小: 滑块 (0-500)
  - 最小块大小: 滑块 (50-500)

代码块处理:
  - 处理策略: [混合] (保留原样 | LLM摘要 | 混合)
  - 摘要阈值: 数字输入 (500字符)
  - LLM模型选择: (使用系统配置的LLM)

检索配置:
  - 检索模式: [纯向量 | 混合检索 | 图检索]
  - 默认Top-K: 滑块 (1-20)
  - 相似度阈值: 滑块 (0-1)

知识图谱配置 (GraphRAG 预留):
  - 启用图谱提取: 开关
  - 实体类型: 多选 [概念, 方法, 工具, 人物]
  - 关系类型: 多选 [包含, 依赖, 等价, 对比]
```

### 4.4 召回测试 Tab（增强）

**新增功能**:
- 配置临时覆盖（测试不同参数效果）
- 批量测试（上传测试用例 CSV）
- 结果可视化（相似度分布图）
- 导出测试报告

### 4.5 知识图谱 Tab（预留）

**功能**（GraphRAG Phase 2）:
- 实体列表
- 关系图可视化
- 实体/关系编辑

### 4.6 UI 组件规划

使用 shadcn + magic_ui_design 打造科技感：

| 组件 | 来源 | 用途 |
|------|------|------|
| Card | shadcn | 知识库卡片 |
| Slider | shadcn | 参数调节滑块 |
| Select | shadcn | 下拉选择 |
| Table | shadcn | 文档块列表 |
| Badge | shadcn | 状态标签 |
| Dialog | shadcn | 编辑弹窗 |
| Switch | shadcn | 开关控件 |
| Tabs | shadcn | Tab 切换 |
| Border Beam | magic_ui | 卡片边框动画 |
| Shimmer Button | magic_ui | 主要操作按钮 |
| Text Animate | magic_ui | 标题动画 |
| Animated Gradient Text | magic_ui | 强调文本/状态 |
| Meteors | magic_ui | 页面装饰 |
| Grid Pattern | magic_ui | 背景网格 |
| Blur Fade | magic_ui | 内容入场动画 |
| Number Ticker | magic_ui | 统计数字动画 |

---

## 五、实施计划

### Phase 1: 数据模型与基础 API（2天）

- [ ] 创建 `KnowledgeBaseConfig` 模型
- [ ] 创建 `DocumentChunk` 模型
- [ ] 实现知识库配置 CRUD API
- [ ] 数据库迁移

### Phase 2: 切分策略优化（2天）

- [ ] 实现 `MarkdownChunkingStrategy`
- [ ] 实现 `CodeBlockProcessor`（含 LLM 摘要）
- [ ] 修改 `RAGService` 支持知识库级配置
- [ ] 单元测试

### Phase 3: 文档块管理 API（1天）

- [ ] 实现文档块列表/详情 API
- [ ] 实现文档块编辑/删除 API
- [ ] 实现索引重建 API（异步任务）

### Phase 4: 前端页面开发（3天）

- [ ] 知识库列表页面
- [ ] 知识库配置页面
- [ ] 文档块管理页面
- [ ] 召回测试页面增强
- [ ] UI 组件集成（shadcn + magic_ui）

### Phase 5: 测试与文档（1天）

- [ ] 集成测试
- [ ] 变更文档编写
- [ ] 使用文档更新

---

## 六、技术要点

### 6.1 代码块 LLM 摘要提示词

```markdown
你是一位技术文档专家。请为以下代码生成简洁的摘要，用于语义检索。

要求：
1. 摘要长度控制在 100-200 字
2. 说明代码的主要功能和用途
3. 提及关键函数/类名
4. 使用中文

代码语言: {language}

```{language}
{code}
```

请直接输出摘要，不要有任何前缀。
```

### 6.2 索引重建流程

```
1. 接收重建请求
2. 创建异步任务
3. 清除旧索引（可选）
4. 遍历课程章节
5. 按策略切分文档
6. 处理代码块（如需摘要，调用 LLM）
7. 生成 Embedding
8. 写入 ChromaDB
9. 更新 document_chunks 表
10. 更新 chapter_kb_configs 状态
```

### 6.3 配置优先级

```python
def get_effective_config(chapter_id: str, request_config: dict = None) -> dict:
    """
    获取有效配置（合并三层配置）
    """
    # 1. 全局默认配置
    config = load_default_config()
    
    # 2. 章节级配置覆盖
    kb_config = get_chapter_kb_config(chapter_id)
    if kb_config:
        config.update(kb_config)
    
    # 3. 请求级配置覆盖
    if request_config:
        config.update(request_config)
    
    return config
```

### 6.4 元数据回填机制

```python
async def backfill_metadata(course_id: str, chapter_id: str, temp_ref: str):
    """
    导入课程时回填元数据
    
    场景：Embedding 在导入系统前生成，此时没有 course_id/chapter_id
    导入后通过 temp_ref（文件路径）匹配并回填
    """
    # 1. 查找待回填的配置
    configs = db.query(ChapterKBConfig).filter(
        ChapterKBConfig.temp_ref == temp_ref,
        ChapterKBConfig.metadata_backfilled == False
    ).all()
    
    # 2. 回填 course_id 和 chapter_id
    for config in configs:
        config.course_id = course_id
        config.chapter_id = chapter_id
        config.metadata_backfilled = True
    
    # 3. 回填文档块
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.kb_config_id.in_([c.id for c in configs])
    ).all()
    
    for chunk in chunks:
        chunk.course_id = course_id
        chunk.chapter_id = chapter_id
        chunk.metadata_backfilled = True
    
    db.commit()
    
    # 4. 更新 ChromaDB 元数据
    # (可选，取决于是否需要在向量库中按 course_id 过滤)
```

### 6.5 模型状态检测 API

```python
@router.get("/api/admin/rag/status")
async def get_rag_status():
    """
    获取 RAG 模型状态
    
    检测 Embedding 和 Rerank 模型是否可用
    """
    status = {
        "embedding": {
            "available": False,
            "provider": None,
            "model": None,
            "message": None
        },
        "rerank": {
            "available": False,
            "provider": None,
            "model": None,
            "message": None
        }
    }
    
    # 检测 Embedding
    try:
        rag_service = RAGService.get_instance()
        # 尝试 encode 一个简单文本
        rag_service.embedding_model.encode(["test"])
        status["embedding"]["available"] = True
        status["embedding"]["provider"] = rag_service._config.get("embedding", {}).get("provider")
        status["embedding"]["model"] = rag_service._config.get("embedding", {}).get(
            rag_service._config.get("embedding", {}).get("provider"), {}
        ).get("model")
        status["embedding"]["message"] = "Embedding 模型已就绪"
    except Exception as e:
        status["embedding"]["message"] = f"Embedding 不可用: {str(e)}"
    
    # 检测 Rerank（可选）
    try:
        rag_service = RAGService.get_instance()
        if rag_service.reranker is not None:
            status["rerank"]["available"] = True
            status["rerank"]["message"] = "Rerank 模型已就绪"
        else:
            status["rerank"]["message"] = "Rerank 未配置"
    except Exception as e:
        status["rerank"]["message"] = f"Rerank 不可用: {str(e)}"
    
    return status
```

---

## 七、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 摘要延迟 | 索引重建耗时长 | 异步任务 + 进度显示 |
| 代码块摘要质量 | 召回效果下降 | 提供预览功能，允许手动调整 |
| 配置复杂度 | 用户上手困难 | 提供预设模板 + 智能推荐 |
| 大量文档块 | 页面性能 | 分页 + 虚拟滚动 |

---

## 八、验收标准

1. **功能完整性**
   - [ ] 可创建/编辑/删除章节知识库配置
   - [ ] 可按策略切分 Markdown 文档
   - [ ] 代码块混合处理策略生效（短代码保留，长代码LLM摘要）
   - [ ] 文档块管理页面可用（列表、编辑、禁用）
   - [ ] 召回测试功能正常
   - [ ] 元数据回填机制工作正常
   - [ ] 模型状态检测显示正确
   - [ ] 无 Embedding 时功能禁用

2. **GraphRAG 预留**
   - [ ] 数据模型包含知识图谱字段
   - [ ] 配置界面包含图谱选项（可禁用）
   - [ ] API 预留图谱相关端点

3. **性能要求**
   - [ ] 文档块列表加载 < 1s
   - [ ] 单次检索 < 500ms
   - [ ] 索引重建有进度反馈
   - [ ] LLM 摘要异步处理

4. **UI 要求**
   - [ ] 使用 shadcn + magic_ui 组件
   - [ ] 科技感设计风格
   - [ ] 响应式布局
   - [ ] 状态指示清晰（Embedding/Rerank 就绪状态）

---

## 九、依赖关系

### 9.1 LLM 模块联动

代码块摘要功能需要调用系统配置的 LLM：

```python
from app.llm import get_llm_client

async def summarize_code(code: str, language: str) -> str:
    """使用 LLM 生成代码摘要"""
    llm = get_llm_client()
    
    prompt = f"""你是一位技术文档专家。请为以下代码生成简洁的摘要...

代码语言: {language}

```{language}
{code}
```
"""
    
    response = await llm.chat([
        {"role": "system", "content": "你是技术文档专家"},
        {"role": "user", "content": prompt}
    ], temperature=0.3)
    
    return response
```

### 9.2 向量存储依赖

- ChromaDB（已有）
- Collection 按 chapter_id 命名：`chapter_{chapter_id}`

---

*文档版本: v1.0*  
*创建日期: 2026-02-20*
