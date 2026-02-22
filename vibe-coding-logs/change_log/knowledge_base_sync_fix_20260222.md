# 知识库同步查询问题修复日志

**日期**: 2026-02-22  
**分支**: `embedding_system`  
**问题**: 线上环境文档块同步成功但查不到  
**状态**: ✅ 已修复

---

## 一、问题现象

1. **本地环境正常**：查询本地分块（`course_local_xxx`）能正确返回数据
2. **线上环境异常**：一键同步提示成功，但查询线上分块（`course_online_xxx`）返回 0 条记录
3. **触发背景**：刚进行了业务标识重构（`course_id → course_code`, 引入 `chapter_code`）

---

## 二、问题根因

### Bug #1: `list_chapter_chunks_by_id` 函数中 `dir_name` 未定义 【致命】

**位置**: `src/backend/app/api/admin_kb.py`

**问题**: 变量 `dir_name` 从未被赋值，导致 `NameError`，被 try-except 捕获后返回空列表。

**修复**: 添加 `dir_name = course_dir.name`

### Bug #2: `sync-to-db` 和 `sync-all` 的 metadata 字段不一致

**问题**: 两种同步方式产生的数据结构不一致，查询时无法统一处理。

### Bug #3: 查询接口使用旧的 metadata 字段

**问题**: `sync-all` 同步后删除了 `chapter_id` 字段，但查询逻辑仍在检查 `chapter_id`。

---

## 三、修复方案

### 3.1 统一 metadata 字段命名

**决策**: 完全弃用 `temp_ref` 和 `synced_from`，统一使用新标识符体系：

| 用途 | 字段名 | 示例 |
|------|--------|------|
| 课程标识 | `course_code` | `python_basics` |
| 章节标识 | `chapter_code` | `introduction` |
| 数据库课程 UUID | `db_course_id` | `9e653d8a-...` |
| 数据库章节 UUID | `db_chapter_id` | `00d7be63-...` |

### 3.2 修改内容

#### sync-to-db 函数（单章节同步）

```python
new_metadata = {
    **old_metadata,
    "course_code": course_code,                    # 课程标识
    "db_course_id": str(db_chapter.course_id),     # 数据库课程 UUID
    "db_chapter_id": str(chapter_id),              # 数据库章节 UUID
    "synced_at": now_iso,
    "strategy_version": CURRENT_STRATEGY_VERSION,
}

# 删除旧字段，避免混淆
new_metadata.pop("chapter_id", None)
new_metadata.pop("course_id", None)
```

#### sync-all 函数（批量同步）

```python
new_metadata = {
    **old_metadata,
    "course_code": course_code,          # 课程标识
    "chapter_code": chapter_code,        # 章节标识
    "db_course_id": str(course.id),      # 数据库课程 UUID
    "db_chapter_id": str(db_chapter.id), # 数据库章节 UUID
    "synced_at": now_iso,
    "strategy_version": CURRENT_STRATEGY_VERSION,
}

# 删除旧字段，避免混淆
new_metadata.pop("chapter_id", None)
new_metadata.pop("course_id", None)
```

#### 查询过滤（list_chapter_chunks_by_id）

```python
# 使用 db_chapter_id 字段过滤
if metadata.get("db_chapter_id") != chapter_id:
    continue
```

**注意**: 不保留旧字段兼容检查，这是新功能，必须干净。

---

## 四、修复清单

| 修复项 | 文件 | 行号 | 状态 |
|--------|------|------|------|
| 添加 `dir_name = course_dir.name` | admin_kb.py | ~973 | ✅ |
| 删除 `synced_from` 字段 | admin_kb.py | ~664 | ✅ |
| 删除查询时的旧字段兼容检查 | admin_kb.py | ~978 | ✅ |
| 统一 metadata 字段命名 | admin_kb.py | 多处 | ✅ |

---

## 五、测试验证

```bash
cd src/backend
uv run pytest tests/test_sync_functionality.py -v

# 结果：9 passed
```

---

## 六、C 端影响评估（待后续统一解决）

### 当前状态

- C 端 AI 助手目前**只使用章节 markdown 内容，未接入 RAG**
- C 端广泛使用数据库 UUID（`course_id`, `chapter_id`）

### 潜在问题

当 C 端要接入 RAG 时：

1. **标识符不匹配**：
   - C 端传入 `chapter_id`（UUID）
   - RAG 使用 `course_code` 命名 collection
   - 需要 UUID → course_code 的映射

2. **解决方案**（待后续实施）：
   - 在 `Course` 和 `Chapter` 模型中确保 `code` 字段完整
   - RAG 检索时先通过 UUID 查询获取 code，再访问向量存储

---

## 七、后续待办

1. [ ] 前端 API 层的 `temp_ref` 参数迁移到 `course_code` + `chapter_code`
2. [ ] C 端 RAG 接入：统一 UUID 与 code 的映射机制
3. [ ] 添加单元测试：覆盖同步和查询的完整链路

---

## 八、参考文档

- [标识符使用规范](../../docs/identifier_conventions.md)
- [知识库同步功能重构日志](./knowledge_base_sync_refactor_20260221.md)
