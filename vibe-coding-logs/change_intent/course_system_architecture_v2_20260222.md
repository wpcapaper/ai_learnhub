# 课程系统架构简化方案 v2（已完成）

**日期**: 2026-02-22  
**分支**: `system_refactor`  
**状态**: ✅ 已实施

---

## 一、核心设计：三层目录结构

```
raw_courses/              # Layer 1: 原始课程（各种格式）
     │
     ▼ CoursePipeline
markdown_courses/         # Layer 2: 转换后的 markdown（可优化、可预览）
  ├── python_basics_v1/   # 版本号后缀，保留历史
  ├── python_basics_v2/
  └── ml_course_v1/
     │
     ▼ 确认后入库
courses/{course_id}/      # Layer 3: 正式课程（已入库，可启用）
```

---

## 二、已实施变更

### Phase 1: 数据模型调整 ✅

| 变更项 | 修改内容 |
|--------|----------|
| Course.code | 去掉 unique key，允许多版本 |
| Course.is_active | 默认值改为 False（需手动启用） |
| Chapter.code | 删除字段 |
| Chapter.is_active | 新增字段 |

### Phase 2: Pipeline 输出调整 ✅

| 变更项 | 修改内容 |
|--------|----------|
| 输出目录 | `markdown_courses/{course_id}_v{N}/` |
| 版本号 | 自动递增（`_get_next_version()`） |
| admin.py | 新增 `get_markdown_courses_dir()` |

### Phase 3: Embedding 系统简化 ✅

| 删除项 | 行数 |
|--------|------|
| sync-to-db 端点 | ~150 行 |
| sync-all 端点 | ~170 行 |
| **总计** | ~320 行 |

**注意**：`course_local_xxx` / `course_online_xxx` collection 逻辑仍保留在 `jobs.py`，后续可进一步重构。

### Phase 4: API 调整 ✅

| 新增接口 | 功能 |
|----------|------|
| `PUT /admin/database/courses/{id}/activate` | 启用/停用课程 |

### Phase 5: 测试验证 ✅

- 所有核心模块可正常导入
- 语法检查通过

---

## 三、决策确认

| # | 事项 | 决策 | 状态 |
|---|------|------|------|
| 1 | markdown_courses 版本管理 | 版本号后缀，保留历史 | ✅ 已实施 |
| 2 | course_code unique key | 去掉，允许同名多版本 | ✅ 已实施 |
| 3 | chapter_code 字段 | 删除 | ✅ 已实施 |
| 4 | Chapter 标识符 | 统一用 UUID | ✅ 已实施 |
| 5 | Embedding 时机 | 入库时生成，与 is_active 无关 | ✅ 已实施 |
| 6 | 数据迁移 | 推倒重来 | ✅ 已实施 |

---

## 四、提交记录

```
4150833 refactor: Phase 4 - 添加课程启用/停用接口
07227d9 refactor: Phase 3 - 删除 sync-to-db 和 sync-all 同步端点
4c48c0e refactor: Phase 2 - Pipeline 输出调整到 markdown_courses/{name}_v{N}/
a380a24 refactor: 课程系统架构简化 Phase 1 - 数据模型调整
```

---

## 五、后续工作（可选）

1. **简化 ChromaDB collection**
   - 将 `course_local_xxx` / `course_online_xxx` 统一为 `course_xxx`
   - 删除 `jobs.py` 中的 local/online 逻辑

2. **课程优化 Agent**
   - 在 `course_pipeline/optimizer/` 新增模块
   - 实现内容润色、章节重排等 Skills

3. **前端适配**
   - 更新 Admin 前端适配新的 API
   - 删除已废弃的 sync 相关调用
