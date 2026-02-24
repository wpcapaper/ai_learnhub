# RAG 架构设计规范

本文档定义 RAG（检索增强生成）模块的架构标准，与 `FILE_LIFE_CIRCLE.md` 共同构成系统架构文档体系。

---

## 文档定位

| 文档 | 关注点 | 目标读者 |
|------|--------|----------|
| FILE_LIFE_CIRCLE.md | 课程数据生命周期 | 内容管理、运维 |
| **RAG_ARCHITECTURE.md** | 向量检索与知识图谱 | RAG 开发、算法优化 |

---

## 设计原则

1. **课程级 Collection**：一个课程一个 Collection，避免章节级 Collection 爆炸
2. **Metadata 精简高效**：只存储必要字段，支持高效过滤和精准追溯
3. **知识图谱解耦**：图谱数据独立存储，通过位置信息关联原文
4. **版本管理集中化**：course.json 作为版本管理的单一事实来源
5. **标识符统一**：使用 `code`（目录名）作为跨系统主标识

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAG 架构总览                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐           │
│  │  course.json    │     │   ChromaDB      │     │   知识图谱       │           │
│  │  (版本管理)      │     │   (向量检索)     │     │   (图检索)       │           │
│  │                 │     │                 │     │                 │           │
│  │  code           │     │  course_{code}  │     │  Entity         │           │
│  │  kb_version: 1  │────►│  ┌───────────┐  │     │  - code         │           │
│  │  kg_version: 1  │     │  │   Chunk   │  │◄───►│  - source_file  │           │
│  │                 │     │  │ metadata  │  │     │  - char_range   │           │
│  └─────────────────┘     │  └───────────┘  │     │                 │           │
│                          └─────────────────┘     └─────────────────┘           │
│                                                                                 │
│  关键关联：                                                                      │
│  • Chunk → code + source_file + char_range → 精准定位原文                        │
│  • Entity → code + source_file + char_range → 追溯来源                           │
│  • kb_version → course.json 单一管理                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 一、Collection 策略

### 1.1 命名规则

```
命名格式: course_{code}_{kb_version}
示例:     course_python_basics_1
          course_python_basics_2
```

**说明**：
- `code` 为课程目录名（见 FILE_LIFE_CIRCLE.md）
- `kb_version` 为知识库版本号，来自 course.json
- 一个课程 + 版本 对应一个 Collection
- 历史版本 Collection 保留，支持无缝回滚

### 1.2 为什么选择课程级而非章节级

| 对比项 | 章节级 Collection | 课程级 Collection |
|--------|-------------------|-------------------|
| Collection 数量 | O(章节数)，易爆炸 | O(课程数)，可控 |
| 跨章节检索 | 需要多 Collection 合并 | 直接检索，性能好 |
| 管理复杂度 | 高 | 低 |
| 数据隔离 | 强 | 通过 metadata 过滤 |

**结论**：采用课程级 Collection，章节隔离通过 metadata 实现。

### 1.3 版本化 Collection 管理

```
course_python_basics_1  ← 版本1（历史，可回滚）
course_python_basics_2  ← 版本2（当前活跃）
course_python_basics_3  ← 版本3（索引中，未激活）
```

**版本切换流程**：
1. 索引新版本 → 创建 `course_{code}_{new_version}`
2. 激活新版本 → 更新 `current_kb_version` 配置
3. 查询路由 → 使用 `course_{code}_{current_kb_version}`
4. 清理旧版本 → 删除 N 个版本前的 Collection（可选）

---

## 二、Chunk Metadata 规范

### 2.1 字段定义

```python
CHUNK_METADATA = {
    # === 核心标识（必填）===
    "code": str,              # 课程代码（目录名）
    "source_file": str,       # 相对于课程目录的文件路径，如 "01_intro.md"
    "position": int,          # chunk 在文件中的序号（0-based）
    
    # === 精准定位（知识图谱追溯需要）===
    "char_start": int,        # 原文起始字符位置
    "char_end": int,          # 原文结束字符位置
    
    # === 内容类型 ===
    "content_type": str,      # paragraph/code/table/heading/list
    
    # === 统计字段（保留，用于管理展示）===
    "char_count": int,        # 字符数
    "estimated_tokens": int,  # 估算 token 数
    
    # === 版本管理 ===
    "kb_version": int,        # 当前 Collection 的版本号（与命名一致）
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 用途 | 示例 |
|------|------|:----:|------|------|
| `code` | str | ✅ | 课程唯一标识 | `"python_basics"` |
| `source_file` | str | ✅ | 追溯原文档 | `"01_intro.md"` |
| `position` | int | ✅ | chunk 排序、去重 | `5` |
| `char_start` | int | ✅ | 精确定位、高亮 | `1234` |
| `char_end` | int | ✅ | 精确定位、高亮 | `1456` |
| `content_type` | str | ✅ | 过滤、特殊处理 | `"paragraph"` |
| `char_count` | int | ⚪ | 管理展示 | `222` |
| `estimated_tokens` | int | ⚪ | 管理展示 | `111` |
| `kb_version` | int | ✅ | 版本标识 | `1` |

### 2.3 Chunk ID 生成规则

```python
def generate_chunk_id(code: str, source_file: str, position: int) -> str:
    """
    生成稳定的 chunk ID
    
    格式: {code}__{file_hash}__{position:04d}
    示例: python_basics__a1b2c3d4__0005
    """
    file_hash = hashlib.md5(source_file.encode()).hexdigest()[:8]
    return f"{code}__{file_hash}__{position:04d}"
```

**设计理由**：
- 基于内容位置而非随机 UUID，支持幂等索引
- 同一文件重新索引，相同位置的 chunk ID 不变
- 便于调试和问题定位

### 2.4 过滤查询示例

```python
# 按章节过滤
results = collection.query(
    query_texts=["什么是变量？"],
    where={"source_file": "02_variables.md"},
    n_results=5
)

# 按内容类型过滤
results = collection.query(
    query_texts=["示例代码"],
    where={"content_type": "code"},
    n_results=5
)

# 版本管理通过 Collection 命名实现，无需在 metadata 中过滤版本
```

---

## 三、知识图谱数据模型（预规划）

### 3.1 设计原则

1. **独立存储**：知识图谱数据不嵌入 ChromaDB，使用独立的图存储（Neo4j 等）
2. **位置追溯**：通过 `code + source_file + char_range` 追溯原文，不依赖 chunk_id
3. **预埋字段**：当前预留配置字段，实际实现时扩展

### 3.2 Entity 实体模型

```python
ENTITY_SCHEMA = {
    # === 核心标识 ===
    "id": str,                    # UUID
    "title": str,                 # 实体名称
    "type": str,                  # 实体类型: concept/method/tool/person/organization
    
    # === 来源追溯（关键！）===
    "code": str,                  # 课程代码
    "source_file": str,           # 源文件路径
    "char_start": int,            # 在原文中的字符起始位置
    "char_end": int,              # 在原文中的字符结束位置
    
    # === 可选属性 ===
    "description": str,           # LLM 生成的描述
    "description_embedding": list,# 描述向量（用于语义检索）
    "confidence": float,          # 提取置信度 0-1
    
    # === 图谱结构（可选）===
    "community_id": str,          # 社区检测结果
    "rank": int,                  # 重要性排名
}
```

### 3.3 Relationship 关系模型

```python
RELATIONSHIP_SCHEMA = {
    # === 核心标识 ===
    "id": str,                    # UUID
    "source_entity": str,         # 源实体名称
    "target_entity": str,         # 目标实体名称
    "type": str,                  # 关系类型: related_to/depends_on/contains
    
    # === 来源追溯 ===
    "code": str,                  # 课程代码
    "source_file": str,           # 源文件路径
    "char_start": int,            # 关系在原文中的起始位置
    "char_end": int,              # 关系在原文中的结束位置
    
    # === 可选属性 ===
    "description": str,           # 关系描述
    "weight": float,              # 边权重
    "confidence": float,          # 提取置信度
}
```

### 3.4 追溯原文流程

```
Entity/Relationship
       │
       │  code + source_file + char_range
       ▼
┌─────────────────────────────────────┐
│  markdown_courses/{code}/{file}     │
│  content[char_start:char_end]       │
└─────────────────────────────────────┘
```

**为什么不用 chunk_id**：
- chunk_id 在重新索引后会变化
- char_range 相对于原文位置，更稳定
- 重新切分后可通过 char_range 重新定位

### 3.5 预留配置字段

当前在 `ChapterKBConfig` 中已预留：

```python
# 启用开关
enable_graph_extraction = Column(Boolean, default=False)

# 实体类型配置
graph_entity_types = Column(JSON)    # ["概念", "方法", "工具"]

# 关系类型配置
graph_relation_types = Column(JSON)  # ["包含", "依赖", "相关"]

# 统计字段
graph_entity_count = Column(Integer, default=0)
graph_relation_count = Column(Integer, default=0)
```

---

## 四、版本管理策略

### 4.1 course.json 扩展

```json
{
  "code": "python_basics",
  "title": "Python 基础",
  "description": "Python 入门教程",
  
  // === RAG 版本管理（预埋）===
  "kb_version": 1,
  "kb_updated_at": "2026-02-24T10:00:00Z",
  "kb_config": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "strategy": "semantic"
  },
  
  // === 知识图谱版本（预埋）===
  "kg_version": 1,
  "kg_updated_at": "2026-02-24T10:00:00Z",
  
  "chapters": [...]
}
```

### 4.2 版本化 Collection 管理

**版本命名**：
```
course_{code}_{kb_version}

示例：
course_python_basics_1  # kb_version=1
course_python_basics_2  # kb_version=2
course_python_basics_3  # kb_version=3
```

**版本生命周期**：

```
时间线：
─────────────────────────────────────────────────────►

v1 活跃           v2 索引中         v2 激活        v1 清理
├────────────────►├────────────────►├──────────────►
                  (后台)                            (可选)

查询: v1          查询: v1          查询: v2
```

**核心流程**：

```python
# 1. 索引新版本（后台）
new_version = current_version + 1
collection_name = f"course_{code}_{new_version}"
# 索引所有 chunk，metadata.kb_version = new_version

# 2. 激活新版本（原子切换）
course.kb_version = new_version  # 更新 course.json 或数据库

# 3. 查询路由
active_collection = f"course_{code}_{course.kb_version}"
results = chroma.query(..., collection=active_collection)

# 4. 清理旧版本（可选，保留最近 N 个版本）
if course.kb_version > KEEP_VERSIONS:
    old_collection = f"course_{code}_{course.kb_version - KEEP_VERSIONS}"
    chroma.delete_collection(old_collection)
```

**优势**：
- **原子切换**：改一个配置即完成版本切换
- **无损回滚**：历史版本完整保留
- **并发安全**：新版本索引不影响当前服务
- **灵活清理**：可配置保留 N 个历史版本

### 4.3 无缝更新示意

```
时间线：
─────────────────────────────────────────────────────►

旧版本服务中        新版本索引中         切换        清理
kb_version=1       kb_version=2                    
                   (后台)                           
                                                     
查询过滤:           查询过滤:            查询过滤:   
kb_version=1       kb_version=1         kb_version=2
                   + 后台写入 2          
```

---

## 五、与 FILE_LIFE_CIRCLE 的对齐

### 5.1 生命周期对应关系

| 课程生命周期阶段 | RAG 状态 | 说明 |
|-----------------|----------|------|
| raw_courses（原始） | 无索引 | 未转换，无 RAG 数据 |
| markdown_courses（转换后） | 可索引 | 使用 code 建立索引 |
| 数据库导入 | 无变化 | RAG 数据与数据库无关 |
| 内容更新 + kb_version++ | 触发重索引 | 检测版本变化 |

### 5.2 标识符使用规范

| 场景 | 使用标识 | 示例 |
|------|----------|------|
| Collection 命名 | `code` + `kb_version` | `course_python_basics_1` |
| Chunk metadata | `code` | `"python_basics"` |
| 知识图谱关联 | `code` | `"python_basics"` |
| 数据库查询 | `id` (UUID) | 查到 code 后再访问 RAG |

### 5.3 API 参数转换

```python
# 前端传 UUID，后端转 code
def get_rag_chunks(course_id: str):  # course_id 是 UUID
    course = db.query(Course).filter(Course.id == course_id).first()
    code = course.code  # 转换为 code
    collection_name = f"course_{code}_{course.kb_version}"
    # ... RAG 操作
```

---

## 六、API 规范

### 6.1 知识库管理 API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/admin/kb/status` | GET | 获取 RAG 系统状态 |
| `/api/admin/kb/chapters/config` | GET/PUT | 获取/更新章节配置 |
| `/api/admin/kb/chapters/reindex` | POST | 重建章节索引 |
| `/api/admin/kb/chunks` | GET | 获取章节分块列表 |
| `/api/admin/kb/chapters/test-retrieval` | POST | 召回测试 |

### 6.2 参数规范

```python
# 未导入课程（本地数据源）
GET /api/admin/kb/chapters/config?temp_ref={code}/{file}

# 已导入课程（数据库关联）
GET /api/admin/kb/chapters/{chapter_id}/config
# 内部转换: chapter_id → chapter.course.code → code
```

### 6.3 响应格式

```python
# Chunk 列表响应
{
    "chunks": [
        {
            "id": "python_basics__a1b2c3d4__0005",
            "content": "变量是存储数据的容器...",
            "metadata": {
                "code": "python_basics",
                "source_file": "02_variables.md",
                "position": 5,
                "char_start": 1234,
                "char_end": 1456,
                "content_type": "paragraph",
                "char_count": 222,
                "estimated_tokens": 111,
                "kb_version": 1
            }
        }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20
}
```

---

## 七、迁移计划

### 7.1 当前实现与目标差异

| 项目 | 当前实现 | 目标架构 | 迁移优先级 |
|------|----------|----------|:----------:|
| Collection 命名 | `chapter_{id}` 混用 | `course_{code}_{version}` | 高 |
| Metadata 字段 | 多冗余字段 | 精简必要字段 | 中 |
| Chunk ID | 随机 UUID | 稳定位置 ID | 中 |
| 版本管理 | chunk 级 strategy_version | course.json kb_version | 低 |

### 7.2 迁移步骤

1. **Phase 1: Collection 合并**
   - 创建课程级 Collection
   - 迁移章节级数据
   - 更新 API 参数

2. **Phase 2: Metadata 规范化**
   - 添加 char_start/char_end
   - 统一 source_file 格式
   - 清理冗余字段

3. **Phase 3: 版本管理（RAG 优化模块实现时）**
   - 扩展 course.json
   - 实现版本检测逻辑
   - 实现无缝更新流程

---

## 八、术语表

| 术语 | 说明 |
|------|------|
| `code` | 课程代码，目录名，跨系统唯一标识 |
| `chunk` | 文档分块，RAG 检索的基本单元 |
| `kb_version` | 知识库版本号，管理 embedding 更新 |
| `kg_version` | 知识图谱版本号 |
| `char_range` | 字符位置范围 (char_start, char_end) |
| `temp_ref` | 临时引用，格式为 `{code}/{file}` |

---

## 九、参考资料

- [Microsoft GraphRAG 数据模型](https://github.com/microsoft/graphrag)
- [ChromaDB Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering)
- [FILE_LIFE_CIRCLE.md](./FILE_LIFE_CIRCLE.md) - 课程数据生命周期

---

## 更新日志

- **2026-02-24**: 初始文档创建，确立课程级 Collection、精简 Metadata、知识图谱预规划架构
