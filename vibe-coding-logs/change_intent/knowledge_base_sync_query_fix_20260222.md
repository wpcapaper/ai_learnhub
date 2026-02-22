# 知识库同步查询问题修复方案

**日期**: 2026-02-22  
**分支**: `embedding_system`  
**问题**: 线上环境文档块同步成功但查不到  
**根因**: 代码缺陷 + 业务标识重构不完整

---

## 一、问题现象

1. **本地环境正常**：查询本地分块（`course_local_xxx`）能正确返回数据
2. **线上环境异常**：一键同步提示成功，但查询线上分块（`course_online_xxx`）返回 0 条记录
3. **触发背景**：刚进行了业务标识重构（`course_id → course_code`, 引入 `chapter_code`）

---

## 二、问题根因分析

### 2.1 Bug #1: `list_chapter_chunks_by_id` 函数中 `dir_name` 未定义 【致命】

**位置**: `src/backend/app/api/admin_kb.py` 第 962 行

**代码问题**:
```python
# 第 918-1007 行
@router.get("/chapters/{chapter_id}/chunks", response_model=ChunkListResponse)
async def list_chapter_chunks_by_id(chapter_id: str, ...):
    # ... 查找课程目录 ...
    course_dir = None
    for d in courses_base_dir.iterdir():
        # ... 找到 course_dir ...
    
    if not course_dir:
        raise HTTPException(status_code=404, detail="课程目录不存在")
    
    try:
        rag_service = RAGService.get_instance()
        store = ChromaVectorStore(
            collection_name=normalize_collection_name(f"course_online_{dir_name}"),  # ❌ dir_name 未定义!
            persist_directory=rag_service.persist_directory
        )
```

**问题**: 变量 `dir_name` 从未被赋值，应该使用 `course_dir.name`。

**影响**: **致命** - 线上分块查询直接抛出 `NameError`，但被 try-except 捕获后返回空列表，用户看到"查无数据"。

**修复**: 在使用前添加 `dir_name = course_dir.name`

---

### 2.2 Bug #2: `sync-to-db` 和 `sync-all` 的 metadata 字段不一致

**位置**: `src/backend/app/api/admin_kb.py`

**两个同步接口的 metadata 差异**:

| 字段 | sync-to-db (单章节) | sync-all (批量) |
|------|---------------------|-----------------|
| `chapter_id` | ✅ UUID | ❌ 删除 |
| `course_id` | ✅ UUID | ❌ 删除 |
| `db_chapter_id` | ❌ 无 | ✅ UUID |
| `db_course_id` | ❌ 无 | ✅ UUID |
| `course_code` | ❌ 无 | ✅ |
| `chapter_code` | ❌ 无 | ✅ |
| `synced_from` | ✅ temp_ref | ✅ 原chapter_id |

**问题**: 两种同步方式产生的数据结构不一致，查询时无法统一处理。

**影响**: 中等 - 目前前端主要用 `sync-all`，但如果用户用单章节同步，查询会失败。

---

### 2.3 Bug #3: 查询接口使用旧的 metadata 字段

**位置**: `src/backend/app/api/admin_kb.py` 第 971 行

```python
# list_chapter_chunks_by_id 函数
if metadata.get("chapter_id") != chapter_id:  # ❌ 但 sync-all 删除了这个字段!
    continue
```

**问题**: `sync-all` 批量同步时删除了 `chapter_id` 字段，改用 `db_chapter_id`，但查询逻辑仍在检查 `chapter_id`。

**影响**: 高 - 使用 `sync-all` 同步的数据无法被查询到。

---

## 三、修复方案

### 3.1 修复 Bug #1: 定义 dir_name 变量（立即修复）

```python
# admin_kb.py 第 958-964 行
if not course_dir:
    raise HTTPException(status_code=404, detail="课程目录不存在")

# 添加：获取目录名
dir_name = course_dir.name

try:
    rag_service = RAGService.get_instance()
    store = ChromaVectorStore(
        collection_name=normalize_collection_name(f"course_online_{dir_name}"),
        persist_directory=rag_service.persist_directory
    )
```

### 3.2 修复 Bug #2 & #3: 统一 metadata 并更新查询（立即修复）

**决策**: 采用新的标识符体系（与 `docs/identifier_conventions.md` 一致）

| 用途 | 字段名 | 示例 |
|------|--------|------|
| 课程标识 | `course_code` | `python_basics` |
| 章节标识 | `chapter_code` | `introduction` |
| 数据库课程 UUID | `db_course_id` | `9e653d8a-...` |
| 数据库章节 UUID | `db_chapter_id` | `00d7be63-...` |
| 原始文件引用 | `synced_from` | `python_basics/01.md` |

**修改 sync-to-db 函数**:
```python
new_metadata = {
    **old_metadata,
    "course_code": course_code,                    # 课程标识
    "db_course_id": str(db_chapter.course_id),     # 数据库课程 UUID
    "db_chapter_id": str(chapter_id),              # 数据库章节 UUID
    "synced_from": temp_ref,                       # 原始 temp_ref
    "synced_at": now_iso,
    "strategy_version": CURRENT_STRATEGY_VERSION,
}

# 删除旧的 chapter_id 和 course_id，避免混淆
new_metadata.pop("chapter_id", None)
new_metadata.pop("course_id", None)
```

**修改查询过滤条件**:
```python
# 使用新的 db_chapter_id 字段过滤
if metadata.get("db_chapter_id") != chapter_id:
    # 兼容旧数据：也检查旧的 chapter_id 字段
    if metadata.get("chapter_id") != chapter_id:
        continue
```

---

## 四、C 端影响评估（待后续统一解决）

### 4.1 当前状态

- C 端 AI 助手目前**只使用章节 markdown 内容，未接入 RAG**
- C 端广泛使用数据库 UUID（`course_id`, `chapter_id`）

### 4.2 潜在问题

当 C 端要接入 RAG 时：

1. **标识符不匹配**：
   - C 端传入 `chapter_id`（UUID）
   - RAG 使用 `course_code` 命名 collection
   - 需要 UUID → course_code 的映射

2. **解决方案**（待后续实施）：
   - 在 `Course` 和 `Chapter` 模型中确保 `code` 字段完整
   - RAG 检索时先通过 UUID 查询获取 code，再访问向量存储
   - 或在 metadata 中同时存储 `db_chapter_id` 用于 UUID 查询

### 4.3 建议

- 本次修复只涉及 Admin 端（知识库管理页面）
- C 端 RAG 接入需要更全面的重构
- 建议在合并多个分支后统一规划

---

## 五、修改文件清单

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `admin_kb.py` | 修复 dir_name、统一 metadata、更新查询条件 | P0 |

---

## 六、风险与回退

### 风险
- 已同步的线上分块可能需要重新同步（如果使用了旧的 metadata 格式）
- 元数据字段变更可能影响其他依赖方

### 回退方案
- 保留查询时对旧字段 (`chapter_id`, `course_id`) 的兼容性检查
- 如需完全回退，恢复 git 提交

---

## 七、后续待办

1. [ ] 清理脏数据：检查是否已有用旧 metadata 同步的数据
2. [ ] C 端 RAG 接入：统一 UUID 与 code 的映射机制
3. [ ] 添加单元测试：覆盖同步和查询的完整链路

---

## 八、参考文档

- [标识符使用规范](../../docs/identifier_conventions.md)
- [知识库同步功能重构日志](../change_log/knowledge_base_sync_refactor_20260221.md)
- [代码审查报告](./embedding_system_code_review_20260222.md)
