# 文档分块系统说明

## 概述

本文档描述了 AILearn Hub 中 RAG 系统的文档分块（Chunking）子系统。该系统负责将 Markdown 格式的课程文档转换为适合向量检索的文档块。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         文档分块流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────┐    ┌──────────────┐    ┌──────────────┐            │
│   │ Markdown │    │   分块策略    │    │   Chunk +    │            │
│   │   文档   │───▶│  (Strategy)   │───▶│   Metadata   │            │
│   └──────────┘    └──────────────┘    └──────────────┘            │
│                         │                                           │
│                         ▼                                           │
│              ┌─────────────────────┐                               │
│              │  _split_by_headers  │  按标题层级分割                │
│              └─────────────────────┘                               │
│                         │                                           │
│                         ▼                                           │
│              ┌─────────────────────┐                               │
│              │_split_preserve_blocks│  保持代码块/表格完整性        │
│              └─────────────────────┘                               │
│                         │                                           │
│                         ▼                                           │
│              ┌─────────────────────┐                               │
│              │  _split_large_section │  处理超大段落                │
│              └─────────────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. ChunkingStrategy（分块策略基类）

**位置**: `src/backend/app/rag/chunking/strategies.py`

```python
class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(
        self,
        content: str,
        course_id: str,
        chapter_id: Optional[str] = None,
        chapter_title: Optional[str] = None,
        **kwargs
    ) -> List[Chunk]:
        pass
```

**作用**: 定义分块策略的统一接口，支持多种分块算法。

### 2. SemanticChunkingStrategy（语义分块策略）

**主要分块逻辑**，针对 Markdown 文档优化。

#### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `min_chunk_size` | 100 | 最小块大小（字符数） |
| `max_chunk_size` | 1000 | 最大块大小（字符数） |
| `overlap_size` | 200 | 重叠大小（字符数） |

#### 分块流程

```
步骤1: _split_by_headers()
├── 按标题层级（#, ##, ###）分割文档
├── 每个顶级标题及其子内容作为一个整体
└── 保持标题与内容的关联

步骤2: _split_preserve_blocks()
├── 识别代码块（```...```）
├── 识别表格（|...|）
├── 将简短说明（<200字符）与代码块合并
└── 保持特殊结构的完整性

步骤3: _split_large_section()
├── 处理超过 max_chunk_size 的段落
├── 代码块/表格完全不拆分（即使超过阈值）
└── 普通文本按大小拆分
```

### 3. Chunk（文档块数据结构）

**位置**: `src/backend/app/rag/chunking/metadata.py`

```python
@dataclass
class Chunk:
    chunk_id: str           # 唯一标识
    text: str               # 文本内容
    metadata: Dict[str, Any]  # 元数据
    embedding: Optional[list] = None  # 向量（可选）
```

### 4. Metadata（元数据字段）

每个 Chunk 包含以下元数据：

| 字段 | 类型 | 说明 |
|------|------|------|
| `course_id` | str | 课程ID |
| `chapter_id` | str | 章节ID（实际为 collection 名称） |
| `chapter_title` | str | 章节标题 |
| `source_file` | str | 源文件路径（格式：course_id/chapter_file） |
| `position` | int | 在文档中的位置 |
| `content_type` | str | 内容类型（paragraph/code_block/table） |
| `char_count` | int | 字符数 |
| `word_count` | int | 词数 |
| `estimated_tokens` | int | 估算的 token 数 |
| `token_level` | str | token 大小级别（normal/warning/large/oversized） |
| `strategy_version` | str | 分块策略版本号（如 `markdown-v1.0`） |
| `indexed_at` | str | 索引时间（ISO 8601 格式） |

## 版本控制机制

### 概述

为防止历史脏数据污染召回结果，系统实现了基于策略版本的 chunk 版本控制。

### 工作原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                       版本控制流程                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   1. 索引请求                                                        │
│      │                                                              │
│      ▼                                                              │
│   2. 获取该章节的旧版本 chunk IDs                                     │
│      │                                                              │
│      ▼                                                              │
│   3. 写入新版本 chunks（带当前 strategy_version）                     │
│      │                                                              │
│      ▼                                                              │
│   4. 成功后删除旧版本 chunks                                          │
│      │                                                              │
│      ▼                                                              │
│   5. 查询时默认只返回当前版本数据                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 策略版本号格式

```
{策略类型}-v{major}.{minor}

示例：markdown-v1.0
```

- **major**: 不兼容变更（如完全重写分块逻辑）
- **minor**: 兼容性改进（如调整参数、修复边界情况）

### 版本号管理

版本号定义在 `src/backend/app/rag/chunking/strategies.py`:

```python
CHUNK_STRATEGY_VERSION = "markdown-v1.0"
```

**升级场景**：
1. 修改分块算法核心逻辑 → 升级 major
2. 调整参数默认值 → 升级 minor
3. 修复边界情况处理 → 升级 minor

### 查询时的版本过滤

```python
# ChromaVectorStore.search() 默认行为
results = store.search(
    query_embedding=embedding,
    top_k=5,
    filter_legacy=True  # 只返回当前策略版本的数据
)

# 需要查询所有版本时
results = store.search(
    query_embedding=embedding,
    top_k=5,
    filter_legacy=False  # 包含旧版本数据
)
```

### 清理旧版本

```python
# 获取旧版本 chunk 数量统计
stats = store.get_version_stats()
# {"markdown-v1.0": 100, "markdown-v0.9": 20}

# 删除指定源文件的旧版本 chunks
deleted_count = store.delete_legacy_chunks(source_file="course/chapter.md")

# 删除所有旧版本 chunks
deleted_count = store.delete_legacy_chunks()
```

### 优势

1. **防止脏数据污染**：旧版本的低质量分块不会影响召回
2. **平滑迁移**：策略升级时，新旧数据可以共存
3. **可追溯**：每个 chunk 记录了索引时间，便于问题排查
4. **安全删除**：先写后删，避免中途失败导致数据丢失

## 分块规则详解

### 1. 标题层级分割

```
# 一级标题          ─┐
## 二级标题          │ Section 1
内容内容...         │
                    ─┘
# 一级标题          ─┐
## 二级标题          │ Section 2
### 三级标题         │
内容内容...         │
                    ─┘
```

**规则**：
- 顶级标题（`#`）开始新的 section
- 同级或更高级标题会结束当前 section
- 子标题（`##`、`###`）的内容保留在父 section 中

### 2. 代码块处理

**规则**：
- 代码块（```...```）完全不拆分，保持完整性
- 代码块前的简短说明（<200字符）会与代码块合并
- 单独成为一个 chunk，即使超过 `max_chunk_size`

**示例**：

```markdown
#### 提取文字        ← 简短说明（与代码块合并）

```python
def extract_text():
    # 很长的代码...
```
```

上述内容会被合并为一个 chunk，content_type 为 `code_block`。

### 3. 表格处理

**规则**：
- 表格（以 `|` 开头的行）保持完整性
- 不拆分表格

### 4. Token 大小级别

用于帮助用户判断分块设置是否合理：

| 级别 | Token 范围 | 视觉提示 | 建议 |
|------|-----------|---------|------|
| normal | < 512 | 绿色 | 理想大小 |
| warning | 512-1024 | 黄色 | 可接受 |
| large | 1024-2048 | 橙色 + 边框 | 建议调整分块参数 |
| oversized | > 2048 | 红色 + 边框 | 强烈建议调整 |

## 数据存储

### ChromaDB Collection 命名规则

```
collection_name = normalize_collection_name(f"course_{course_id}")
```

**示例**：
- `python_basics` → `course_python_basics`
- `13.向量工程和RAG系统` → `course_13._____RAG___0`

**注意**：ChromaDB 只允许 `[a-zA-Z0-9._-]` 字符，非 ASCII 字符会被替换。

### 存储结构

```
ChromaDB
├── course_python_basics          # 课程级别的 collection
│   ├── chunk_1 (source: python_basics/01_introduction.md)
│   ├── chunk_2 (source: python_basics/01_introduction.md)
│   ├── chunk_3 (source: python_basics/02_variables.md)
│   └── ...
└── course_langchain_intro
    └── ...
```

## API 端点

### 分块相关 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/kb/courses/reindex` | POST | 批量索引课程 |
| `/api/admin/kb/chapters/reindex` | POST | 索引单个章节 |
| `/api/admin/kb/chapters/chunks` | GET | 获取章节的文档块列表 |
| `/api/admin/kb/chunks/{chunk_id}` | GET | 获取文档块详情 |
| `/api/admin/kb/chapters/config` | GET | 获取分块配置 |

### 配置参数（通过 ChapterKBConfig）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `chunking_strategy` | semantic | 分块策略 |
| `chunk_size` | 1000 | 目标块大小 |
| `chunk_overlap` | 200 | 块重叠大小 |
| `min_chunk_size` | 100 | 最小块大小 |
| `code_block_strategy` | hybrid | 代码块处理策略 |

## 前端展示

### Token 分布统计

在文档块列表页面显示当前章节的 token 分布：

```
Token 分布: 正常(<512): 8  偏大(512-1K): 3  较大(1K-2K): 1  过大(>2K): 0
```

### 文档块卡片

每个文档块显示：
- 序号
- 来源文件
- 内容类型标签
- 估算 token 数（带颜色提示）
- 字符数
- 启用/禁用状态
- 内容预览

## 最佳实践

### 1. 调整分块参数

如果发现大量 "过大" 或 "较大" 的 chunk：
- 减小 `chunk_size`（如从 1000 改为 800）
- 代码块不受此限制，会保持完整

### 2. 代码密集型文档

对于包含大量代码的教程：
- 代码块保持完整有利于召回上下文
- 但可能导致单个 chunk 过大
- 考虑在源文档中拆分过长的代码示例

### 3. 混合语言文档

Token 估算是基于混合语言假设（约 2 字符/token）：
- 纯英文文档：实际 token 数可能更少
- 纯中文文档：实际 token 数可能更多

## 相关文件

```
src/backend/app/rag/chunking/
├── __init__.py           # 模块导出
├── strategies.py         # 分块策略实现
├── metadata.py           # Chunk 数据结构和元数据
├── filters.py            # 内容过滤器
└── code_processor.py     # 代码块处理器

src/backend/app/rag/
├── service.py            # RAG 服务入口
└── vector_store/         # 向量存储（ChromaDB）

src/admin-frontend/app/knowledge-base/
└── page.tsx              # 知识库管理页面
```
