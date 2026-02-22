# 标识符使用规范

> **核心原则**：`course_code` 是课程唯一标识，Collection 统一使用 `course_code` 命名。

## 1. 标识符定义

| 标识符 | 类型 | 来源 | 示例 | 说明 |
|--------|------|------|------|------|
| `course_code` | string | `course.json` 中的 `code` 字段 | `python_basics` | **课程唯一标识**，用于 Collection 命名、API 参数 |
| `course.id` | UUID | 数据库自动生成 | `9e653d8a-bd6e-4cee-9aac-f21aac52a552` | 数据库主键，仅用于 DB 关联 |
| `dir_name` | string | 文件系统目录名 | `python_basics` | 课程目录名称，**应与 course_code 保持一致** |
| `chapter.id` | UUID | 数据库自动生成 | `00d7be63-5c87-43ab-ac36-7a7e45f46c7b` | 章节数据库主键 |
| `temp_ref` | string | 格式：`{course_code}/{chapter_file}` | `python_basics/01_introduction.md` | 本地章节引用，用于索引和同步 |

## 2. ChromaDB Collection 命名规范

```
course_{source}_{course_code}
```

- `source`: `local`（本地开发）或 `online`（线上环境）
- `course_code`: 课程的唯一标识（来自 `course.json` 的 `code` 字段）

**示例**:
- 本地 Collection: `course_local_python_basics`
- 线上 Collection: `course_online_python_basics`

**命名函数**: `normalize_collection_name()` 处理特殊字符

## 3. Chunk Metadata 规范

| 字段 | 本地索引 | 线上同步 |
|------|----------|----------|
| `chapter_id` | `temp_ref` 格式 (`python_basics/01_introduction.md`) | 数据库 UUID (`00d7be63-...`) |
| `course_id` | `course_code` (`python_basics`) | 数据库 UUID (`9e653d8a-...`) |
| `synced_from` | 无 | 原始 `temp_ref` |
| `source_file` | 源文件路径 | 继承 |

## 4. API 参数规范

### 4.1 索引相关 API

| API | 参数 | 类型 | 说明 |
|-----|------|------|------|
| `POST /admin/kb/chapters/reindex` | `temp_ref` | string | 本地章节引用 (`course_code/chapter_file`) |
| `POST /admin/kb/chapters/sync-to-db` | `temp_ref`, `chapter_id` | string, UUID | temp_ref=本地引用, chapter_id=数据库UUID |
| `POST /admin/kb/courses/{course_code}/sync-all` | `course_code` | path | 课程唯一标识 |

### 4.2 检索相关 API

| API | 参数 | 类型 | 说明 |
|-----|------|------|------|
| `POST /rag/retrieve` | `course_id` | string | **应为 `course_code`**，非 UUID |
| `GET /rag/collection/{course_id}/size` | `course_id` | path | **应为 `course_code`** |

## 5. 当前问题

### 问题 1: RAG API 参数命名混淆

**现状**:
```python
# rag.py
async def retrieve(request: RetrieveRequest):
    results = await rag_service.retrieve(
        course_id=request.course_id,  # 参数名叫 course_id
        ...
    )
```

**问题**: 
- 参数名是 `course_id`，但实际应传入 `course_code`
- 容易导致调用方传入 UUID，检索失败

**建议修复**:
- 方案 A: 重命名参数为 `course_code`，明确语义
- 方案 B: 同时支持 `course_code` 和 `course_id`（UUID），内部转换

### 问题 2: 元数据中 course_id 不一致

**现状**:
- 本地索引: `course_id = "python_basics"` (code)
- 线上同步: `course_id = "9e653d8a-..."` (UUID)

**问题**: 检索过滤时可能混淆

**建议修复**:
- 统一使用 `course_code` 作为元数据中的课程标识
- 新增 `db_course_id` 字段存储 UUID（如需要）

## 6. 修复检查清单

- [ ] RAG API 参数重命名: `course_id` → `course_code`
- [ ] RAGService 方法参数重命名
- [ ] 前端调用确认传 `course_code`
- [ ] Chunk 元数据统一使用 `course_code`
- [ ] 更新 API 文档

## 7. 数据流示意

```
┌─────────────────────────────────────────────────────────────────┐
│                        索引流程                                   │
├─────────────────────────────────────────────────────────────────┤
│ course.json (code: "python_basics")                              │
│       ↓                                                          │
│ 本地索引 → Collection: course_local_python_basics                │
│           Metadata: course_id=python_basics, chapter_id=temp_ref │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        同步流程                                   │
├─────────────────────────────────────────────────────────────────┤
│ course_local_python_basics → course_online_python_basics        │
│ Metadata 变化:                                                   │
│   chapter_id: temp_ref → UUID                                    │
│   新增: synced_from=temp_ref                                      │
│   course_id: 保持 course_code（建议）或转换为 UUID（当前）          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        检索流程                                   │
├─────────────────────────────────────────────────────────────────┤
│ 前端调用: POST /rag/retrieve { course_id: "python_basics" }      │
│       ↓                                                          │
│ RAGService.retrieve(course_id="python_basics")                   │
│       ↓                                                          │
│ _get_vector_store(course_id="python_basics", source="online")   │
│       ↓                                                          │
│ Collection: course_online_python_basics ← 使用 course_code!      │
└─────────────────────────────────────────────────────────────────┘
```
