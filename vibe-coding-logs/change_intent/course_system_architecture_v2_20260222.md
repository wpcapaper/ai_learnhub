# 课程系统架构简化方案 v2（最终版）

**日期**: 2026-02-22  
**分支**: `system_refactor`  
**状态**: ✅ 设计已确认

---

## 一、核心设计：三层目录结构

```
raw_courses/                    # Layer 1: 原始课程（各种格式）
     │
     ▼ CoursePipeline
markdown_courses/               # Layer 2: 转换后的 markdown（可优化、可预览）
  ├── python_basics_v1/         # 版本号后缀，保留历史
  ├── python_basics_v2/
  └── ml_course_v1/
     │
     ▼ 确认后入库
courses/{course_id}/            # Layer 3: 正式课程（已入库，可启用）
```

### 1.1 各层职责

| 层 | 目录 | 状态 | 职责 |
|----|------|------|------|
| Layer 1 | `raw_courses/` | 原始 | 存放各种格式的原始课程（ipynb, pdf, docx 等） |
| Layer 2 | `markdown_courses/{name}_v{N}/` | 预览 | Pipeline 转换后的 markdown，版本号后缀，可保留历史 |
| Layer 3 | `courses/{course_id}/` | 正式 | 入库后的课程文件，关联数据库记录 |

### 1.2 数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: raw_courses/                                              │
│  ├── python_basics.ipynb                                            │
│  └── ml_course.pdf                                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ CoursePipeline.convert_course()
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2: markdown_courses/                                         │
│  ├── python_basics_v1/    ← 第一版转换                              │
│  │   ├── course.json                                                │
│  │   └── *.md                                                       │
│  ├── python_basics_v2/    ← 第二版转换（优化后）                      │
│  │   ├── course.json                                                │
│  │   └── *.md                                                       │
│  └── ...                                                             │
│                                                                     │
│  [可选] 课程优化 Agent：                                             │
│  - 内容润色                                                          │
│  - 章节重排                                                          │
│  - 长课程拆分                                                        │
│  - 补充元数据                                                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 选择版本后执行"入库"操作
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3: courses/{course_id}/                                      │
│  ├── course.json                                                    │
│  └── *.md                                                           │
│                                                                     │
│  数据库记录：                                                        │
│  - Course: id={course_id}, is_active=false                          │
│  - Chapter: id={chapter_id}, course_id={course_id}                  │
│                                                                     │
│  Embedding：                                                        │
│  - collection: course_{course_id}                                   │
│  - metadata: chapter_id (UUID)                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 手动启用
                     Course.is_active = true
                     （C 端可见）
```

---

## 二、设计决策汇总

### 2.1 标识符策略

| 实体 | 主键 | 其他标识 | 说明 |
|------|------|----------|------|
| Course | `id` (UUID) | `code` (非唯一) | code 保留用于 URL 展示，去掉 unique key |
| Chapter | `id` (UUID) | ~~`code`~~ | **删除 chapter_code 字段** |
| Chunk | `id` (hash) | `chapter_id` (UUID) | metadata 只用 UUID |

### 2.2 版本号策略

**markdown_courses/ 目录命名**：`{course_name}_v{N}/`

```
markdown_courses/
├── python_basics_v1/      # 第一次转换
├── python_basics_v2/      # 优化后的版本
├── python_basics_v3/      # 再次修改
└── ml_course_v1/
```

### 2.3 course_code 约束

```python
# models/course.py - 修改后
code = Column(String(50), nullable=False, index=True)  # 去掉 unique=True
```

### 2.4 Chapter 模型调整

```python
# models/chapter.py - 修改后
class Chapter(Base):
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    # code = Column(String(100))  ← 删除此字段
    title = Column(String(200), nullable=False)
    content_markdown = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False)  # 新增
    sort_order = Column(Integer, default=0)
    # ...
```

### 2.5 Embedding 时机

**决策**：入库时立即生成，与 `is_active` 状态无关

### 2.6 is_active 语义

| is_active | C 端可见 | Admin 可见 | Embedding 状态 |
|-----------|---------|-----------|----------------|
| `false` | ❌ | ✅ | 已生成 |
| `true` | ✅ | ✅ | 已生成 |

---

## 三、简化对比

### 3.1 删除的复杂度

| 删除项 | 原因 |
|--------|------|
| `course_local_xxx` / `course_online_xxx` 双数据源 | 单一 collection |
| sync-to-db / sync-all 同步逻辑 | 不需要同步 |
| temp_ref 临时标识 | 入库时直接用 UUID |
| course_code unique key | 允许多版本存在 |
| chapter_code 字段 | C 端不用，统一用 UUID |
| course_code/chapter_code 在 embedding metadata 中 | 只用 UUID |

### 3.2 简化前后对比

| 方面 | 简化前 | 简化后 |
|------|--------|--------|
| 数据源 | 2 个 (local/online) | 1 个 |
| 标识符 | 5 套 (id, code, temp_ref, db_xx_id, chapter_code) | 2 套 (id, code) |
| 同步逻辑 | sync-to-db, sync-all | 无 |
| Chapter 字段 | code + id | 仅 id |

---

## 四、实施步骤

### Phase 1：数据模型调整
- [ ] Course 模型 `code` 去掉 unique key
- [ ] Course 模型 `is_active` 默认值改为 `False`
- [ ] Chapter 模型删除 `code` 字段
- [ ] Chapter 模型添加 `is_active` 字段
- [ ] 数据库重建（推倒重来）

### Phase 2：目录结构调整
- [ ] 创建 `markdown_courses/` 目录
- [ ] 修改 Pipeline 输出到 `markdown_courses/{name}_v{N}/`
- [ ] 清理旧的 `courses/` 目录结构

### Phase 3：Embedding 系统简化
- [ ] 删除 sync-to-db、sync-all 相关代码
- [ ] 删除 temp_ref 相关逻辑
- [ ] 删除 `course_local_xxx` / `course_online_xxx` 相关逻辑
- [ ] 统一 collection 命名为 `course_{course_id}`
- [ ] metadata 简化为只含 `chapter_id` (UUID)

### Phase 4：API 调整
- [ ] 添加课程转换 API：`POST /admin/courses/convert`
- [ ] 添加课程导入 API：`POST /admin/courses/import`
- [ ] 添加课程启用 API：`PUT /admin/courses/{id}/activate`
- [ ] 更新 C 端查询，统一用 UUID

### Phase 5：课程优化 Agent（可选，后续实施）
- [ ] 在 `course_pipeline/optimizer/` 新增模块
- [ ] 实现内容润色、章节重排等 Skills

---

## 五、API 设计

### 5.1 课程转换（Layer 1 → Layer 2）

```python
POST /admin/courses/convert
{
    "raw_course_path": "raw_courses/python_basics.ipynb",
    "version": 1  # 可选，不传则自动递增
}

# Response
{
    "markdown_path": "markdown_courses/python_basics_v1",
    "chapters": [...],
    "quality_report": {...}
}
```

### 5.2 课程导入（Layer 2 → Layer 3）

```python
POST /admin/courses/import
{
    "markdown_course_path": "markdown_courses/python_basics_v2"
}

# Response
{
    "course_id": "uuid-xxx",
    "chapters": [
        {"id": "uuid-1", "title": "Introduction"},
        {"id": "uuid-2", "title": "Variables"}
    ],
    "embedding_status": "completed",
    "is_active": false
}
```

### 5.3 课程启用/停用

```python
PUT /admin/courses/{course_id}/activate
{
    "is_active": true
}
```

### 5.4 C 端查询

```python
# 获取课程（只返回 is_active=true 的课程）
GET /api/courses/{course_id}

# 获取章节
GET /api/courses/{course_id}/chapters/{chapter_id}

# RAG 检索
POST /api/rag/retrieve
{
    "course_id": "uuid-xxx",
    "query": "什么是变量？"
}
```

---

## 六、决策确认清单

| # | 事项 | 决策 | 状态 |
|---|------|------|------|
| 1 | markdown_courses 版本管理 | 版本号后缀，保留历史 | ✅ 已确认 |
| 2 | course_code unique key | 去掉，允许同名多版本 | ✅ 已确认 |
| 3 | chapter_code 字段 | 删除 | ✅ 已确认 |
| 4 | Chapter 标识符 | 统一用 UUID | ✅ 已确认 |
| 5 | Embedding 时机 | 入库时生成，与 is_active 无关 | ✅ 已确认 |
| 6 | 数据迁移 | 推倒重来 | ✅ 已确认 |

---

## 七、参考

- [标识符使用规范](../../docs/identifier_conventions.md)
- [知识库同步功能重构日志](./knowledge_base_sync_refactor_20260221.md)
- [课程 Pipeline 文档](../../src/backend/app/course_pipeline/README.md)
