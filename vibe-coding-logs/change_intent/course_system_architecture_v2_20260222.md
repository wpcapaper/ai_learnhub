# 课程系统架构简化方案 v2（最终版）

**日期**: 2026-02-22  
**分支**: `system_refactor`  
**状态**: ✅ 已实施

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

### 1.2 API 设计（清晰分离）

| API | 数据源 | 用途 |
|-----|--------|------|
| `GET /api/admin/raw-courses` | `raw_courses/` | 原始课程列表 |
| `GET /api/admin/markdown-courses` | `markdown_courses/` | 已转换课程列表 |
| `GET /api/admin/markdown-courses/{id}/course.json` | `markdown_courses/{id}/` | 课程章节配置 |
| `GET /api/admin/database/courses` | 数据库 | 已入库课程列表 |

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

### 2.3 is_active 语义

| is_active | C 端可见 | Admin 可见 | Embedding 状态 |
|-----------|---------|-----------|----------------|
| `false` | ❌ | ✅ | 已生成 |
| `true` | ✅ | ✅ | 已生成 |

---

## 三、已实施变更

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

### Phase 4: API 调整 ✅

| 新增接口 | 功能 |
|----------|------|
| `PUT /admin/database/courses/{id}/activate` | 启用/停用课程 |
| `GET /admin/markdown-courses` | 已转换课程列表 |
| `GET /admin/markdown-courses/{id}/course.json` | 课程配置 |

### Phase 5: 前端改进 ✅

- 知识库页面使用 `getMarkdownCourses()` 获取已转换课程
- 添加空状态引导界面

---

## 四、Docker 配置

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ./courses:/app/courses
      - ./raw_courses:/app/raw_courses
      - ./markdown_courses:/app/markdown_courses  # 新增
```

---

## 五、提交记录

```
f5c4af3 feat: 架构改进 - 新增 markdown-courses API 和空状态引导
ba622d0 test: 添加课程系统重构单元测试
1422b43 fix: admin.py 批量修复重构遗漏问题
...
```

---

## 六、后续待办

1. [ ] 简化 ChromaDB collection（统一为 `course_{id}`）
2. [ ] 课程优化 Agent（内容润色、章节重排）
3. [ ] C 端 RAG 接入：统一 UUID 与 code 的映射机制

---

## 七、参考

- [标识符使用规范](../../docs/identifier_conventions.md)
- [单元测试](../../src/backend/tests/test_course_refactor.py)
