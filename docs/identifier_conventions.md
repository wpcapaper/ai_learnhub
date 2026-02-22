# 标识符使用规范

> **核心原则**：使用语义化标识符（code），而非数据库 UUID。

## 1. 标识符生命周期

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          完整生命周期                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 课程转换 (CoursePipeline)                                               │
│     raw_course/ ──转换──> courses/{course_code}/course.json                 │
│                              │                                              │
│                              ├─ course.code = "python_basics"               │
│                              └─ chapters[].code = "introduction"            │
│                                                                             │
│  2. 导入到数据库 (Admin API)                                                │
│     courses/ ──导入──> Database                                             │
│                       │                                                     │
│                       ├─ Course.code = "python_basics"                      │
│                       ├─ Course.id = UUID (自动生成)                        │
│                       └─ Chapter.code = "introduction"                      │
│                          Chapter.id = UUID (自动生成)                        │
│                                                                             │
│  3. 本地索引 (Indexing)                                                     │
│     courses/{course_code}/*.md ──索引──> ChromaDB                           │
│                                          │                                  │
│                                          └─ course_local_{course_code}     │
│                                             Metadata:                       │
│                                               course_code                   │
│                                               chapter_code                  │
│                                                                             │
│  4. 同步到线上 (Sync)                                                       │
│     course_local_{course_code} ──同步──> course_online_{course_code}        │
│                                               │                             │
│                                               └─ Metadata 变化:             │
│                                                  + db_course_id (UUID)      │
│                                                  + db_chapter_id (UUID)     │
│                                                  + synced_from              │
│                                                  + synced_at                │
│                                                                             │
│  5. 检索 (Retrieval)                                                        │
│     前端 ──检索请求──> RAG API                                              │
│            │              │                                                 │
│            └─ course_code ┴─> Collection: course_online_{course_code}       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. 标识符定义

| 标识符 | 类型 | 生成位置 | 示例 | 用途 |
|--------|------|----------|------|------|
| `course_code` | string | CoursePipeline | `python_basics` | **课程唯一标识** |
| `chapter_code` | string | CoursePipeline | `introduction` | **章节唯一标识（课程内）** |
| `db_course_id` | UUID | 数据库导入时 | `9e653d8a-...` | 数据库主键 |
| `db_chapter_id` | UUID | 数据库导入时 | `00d7be63-...` | 数据库主键 |

## 3. course.json 结构

```json
{
  "code": "python_basics",
  "title": "Python 基础入门",
  "chapters": [
    {
      "code": "introduction",
      "title": "Python 简介",
      "file": "01_introduction.md",
      "sort_order": 1
    },
    {
      "code": "variables", 
      "title": "变量与数据类型",
      "file": "02_variables.md",
      "sort_order": 2
    }
  ]
}
```

### chapter_code 生成规则

在 `CoursePipeline._generate_chapter_code()` 中：

1. **优先使用已有 code**：如果章节已设置 code，直接使用
2. **从 file_name 提取**：
   - `01_introduction.md` → `introduction`
   - `02_variables.md` → `variables`
   - `ch01-getting-started.md` → `getting_started`
3. **兜底**：使用 `chapter_{sort_order}`

## 4. 数据库模型

### Course 表
```python
id = Column(String(36), primary_key=True)     # UUID
code = Column(String(50), unique=True)        # 课程唯一标识
```

### Chapter 表
```python
id = Column(String(36), primary_key=True)     # UUID
course_id = Column(String(36), ForeignKey)    # 关联课程
code = Column(String(100))                    # 章节唯一标识（课程内）
```

## 5. ChromaDB Collection 命名

```
course_{source}_{course_code}
```

**示例**:
- 本地: `course_local_python_basics`
- 线上: `course_online_python_basics`

## 6. Chunk Metadata 规范

### 本地索引
```json
{
  "course_code": "python_basics",
  "chapter_code": "introduction",
  "source_file": "01_introduction.md",
  "position": 0,
  "content_type": "paragraph",
  "strategy_version": "markdown-v1.0"
}
```

### 线上同步
```json
{
  "course_code": "python_basics",
  "chapter_code": "introduction",
  "db_course_id": "9e653d8a-bd6e-4cee-9aac-f21aac52a552",
  "db_chapter_id": "00d7be63-5c87-43ab-ac36-7a7e45f46c7b",
  "synced_from": "python_basics/01_introduction.md",
  "synced_at": "2026-02-22T12:00:00Z",
  "source_file": "01_introduction.md",
  "position": 0,
  "strategy_version": "markdown-v1.0"
}
```

**禁止使用**：
- ❌ `course_id`（与 UUID 混淆）
- ❌ `chapter_id`（与 UUID 混淆）

## 7. API 参数规范

### RAG 检索
```http
POST /api/rag/retrieve
{
  "query": "什么是变量",
  "course_code": "python_basics"
}
```

### 同步
```http
POST /api/admin/kb/courses/{course_code}/sync-all
```

## 8. 使用场景矩阵

| 场景 | 使用的标识符 | 说明 |
|------|-------------|------|
| Collection 命名 | `course_code` | `course_online_{course_code}` |
| 检索 API | `course_code` | 前端传入课程代码 |
| 索引 API | `course_code` + `chapter_code` | 指定要索引的课程和章节 |
| DB 外键关联 | `db_course_id` / `db_chapter_id` | 数据库关系 |
| Admin 面板展示 | `course_code` | 唯一标识课程 |
| Chunk 过滤 | `chapter_code` | 按章节过滤检索结果 |

## 9. 快速参考

```
course_code    ← 课程唯一标识，贯穿始终
chapter_code   ← 章节唯一标识，课程内唯一
db_*_id        ← 数据库 UUID，仅用于 DB 关联
```
