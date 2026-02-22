# 课程系统架构简化方案分析

**日期**: 2026-02-22  
**分支**: `system_refactor`  
**状态**: 设计评审中

---

## 一、问题背景

当前系统存在过度设计问题，特别是在课程内容管理和 embedding 系统方面引入了不必要的复杂度。

### 1.1 当前架构复杂度

| 模块 | 当前设计 | 引入的复杂度 |
|------|----------|--------------|
| 数据源 | `course_local_xxx` + `course_online_xxx` | 两套 collection，需要同步机制 |
| 同步 | sync-to-db, sync-all | 整个同步逻辑链路 |
| 标识符 | course_code + chapter_code + db_xx_id | 4 套标识符混用 |
| temp_ref | `course_dir/file.md` 格式 | 又一套引用方式 |

### 1.2 问题根源分析

1. **混淆了"开发环境"和"草稿状态"**
   - `course_local` 本意是本地开发时的数据源
   - 但实际需求是区分"草稿"和"已发布"
   - 两者不是同一维度的问题

2. **过早优化 Embedding**
   - 在内容不稳定阶段就生成 embedding
   - 内容变化后 embedding 失效，需要重新同步

3. **标识符体系混乱**
   - UUID（数据库主键）和 code（业务标识）混用
   - C 端用 UUID，Admin 端用 code
   - 查询时需要相互转换

---

## 二、设计初衷回顾

### 2.1 预导入课程的原始设计

```
原始课程（各种格式）
       │
       ▼
┌─────────────────────────────────────┐
│  CoursePipeline.convert_course()    │
│  - 格式转换（ipynb → md）            │
│  - 章节拆分（按 H1 标题）             │
│  - 质量评估                          │
└─────────────────────────────────────┘
       │
       ▼
courses/{course_id}/  ← 预导入课程（全是 markdown）
       │
       │  ← [计划中的课程优化 Agent]
       │     - 重排章节顺序
       │     - 补充课程简介
       │     - 长课程拆分
       │     - 元数据补充
       │
       ▼
┌─────────────────────────────────────┐
│  正式导入到线上                       │
│  - 写入数据库（Course, Chapter）      │
│  - 生成 Embedding                    │
└─────────────────────────────────────┘
```

### 2.2 关键认知

1. **Embedding 应在内容稳定后生成**
   - 如果文本结构会变，embedding 没有意义
   - 课程优化会改变结构，优化后才能做 embedding

2. **课程优化是一次性操作**
   - 课程优化后就没有版本了
   - 不需要 local → online 的同步机制

3. **文档块可以持续修改**
   - 文档块的版本管理是独立的
   - 修改后重新生成 embedding 即可

---

## 三、简化方案

### 3.1 核心原则

1. **单一数据源**：去掉 local/online 双数据源
2. **状态控制**：用 `is_active` 控制可见性
3. **统一标识**：全部使用数据库 UUID

### 3.2 简化后的数据流

```
courses/ (课程内容目录)
    │
    ├── {course_id}/           # 课程目录
    │   ├── course.json        # 课程元数据
    │   ├── 01_intro.md        # 章节内容
    │   ├── 02_*.md
    │   └── ...
    │
    │  ┌────────────────────────────────────────┐
    │  │  课程导入流程                           │
    │  │  1. 创建 Course（is_active=false）      │
    │  │  2. 创建 Chapter 记录                   │
    │  │  3. [可选] 运行课程优化 Agent           │
    │  │  4. 生成 Embedding                     │
    │  │  5. 设置 is_active=true 发布           │
    │  └────────────────────────────────────────┘
    │
    ▼
数据库（Course, Chapter）
    │
    │  is_active=false  →  草稿，C端不可见
    │  is_active=true   →  已发布，C端可见
    │
    ▼
Embedding（单一 collection）
    │
    │  collection: course_{course_id}
    │  metadata: chapter_id, source_file, ...
```

### 3.3 数据模型变更

#### Course 模型（已有 is_active，无需变更）
```python
class Course(Base):
    id = Column(String(36), primary_key=True)
    code = Column(String(50), unique=True)  # 保留，用于 URL
    title = Column(String(200))
    is_active = Column(Boolean, default=False)  # 默认改为 False
    # ... 其他字段
```

#### Chapter 模型（需添加 is_active）
```python
class Chapter(Base):
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'))
    code = Column(String(100))  # 保留，用于 URL
    title = Column(String(200))
    is_active = Column(Boolean, default=False)  # 新增
    # ... 其他字段
```

### 3.4 Embedding 系统简化

#### 当前（复杂）
```
course_local_xxx  ──sync──►  course_online_xxx
     │                            │
  temp_ref                     UUID
```

#### 简化后
```
course_xxx  ←  直接用 course.id 作为 collection 名称
     │
  metadata.chapter_id = chapter.id（UUID）
  metadata.is_active = course.is_active（同步状态）
```

#### 查询时过滤
```python
# C 端检索
def retrieve(self, course_id: str, query: str):
    # 先检查课程是否启用
    course = db.query(Course).filter(Course.id == course_id, Course.is_active == True).first()
    if not course:
        return []
    
    # 直接查询单一 collection
    store = self._get_vector_store(course_id)
    return store.search(query_embedding, filter={"chapter_id": chapter_ids})
```

---

## 四、标识符策略

### 4.1 当前问题

| 标识符 | 用途 | 使用方 | 问题 |
|--------|------|--------|------|
| course.id | 数据库主键 | C端 | UUID 格式 |
| course.code | 业务标识 | URL, Admin | 需要转换 |
| chapter_id | 数据库主键 | C端 | UUID 格式 |
| chapter_code | 业务标识 | Admin | 新增，未统一 |
| temp_ref | 文件引用 | Admin/索引 | 又一套标识 |

### 4.2 统一方案

**原则**：数据库 UUID 为主，code 仅用于 URL 友好展示

| 实体 | 主键 | URL 展示 | 内部引用 |
|------|------|----------|----------|
| Course | `id` (UUID) | `code` | `course_id` |
| Chapter | `id` (UUID) | `code` | `chapter_id` |
| Chunk | `id` (hash) | - | `chapter_id` |

**Embedding metadata**：
```python
metadata = {
    "chapter_id": str(chapter.id),      # UUID，用于查询过滤
    "course_id": str(course.id),        # UUID，用于查询过滤
    "source_file": "01_intro.md",       # 仅用于调试
}
```

**删除 temp_ref**：不再需要 temp_ref，因为内容稳定后才入库。

---

## 五、课程优化 Agent 集成

### 5.1 位置选择

**推荐**：在 `course_pipeline` 模块中新增 `optimizer/` 子模块

```
src/backend/app/course_pipeline/
├── pipeline.py          # 现有：主转换流程
├── converters/          # 现有：格式转换
├── evaluators/          # 现有：质量评估
├── optimizer/           # 新增：课程优化
│   ├── __init__.py
│   ├── content_rewriter.py    # 内容润色
│   ├── chapter_reorganizer.py # 章节重排
│   └── content_splitter.py    # 长章节拆分
```

### 5.2 触发时机

```
Pipeline 转换 ──► courses/ 目录 ──► [优化 Agent] ──► 数据库导入 + Embedding
                                      │
                                      ▼
                              覆盖 courses/ 内容
                              （优化后的版本）
```

**注意**：优化是可选步骤，优化后直接覆盖 courses/ 目录的内容，然后再导入数据库。

### 5.3 与现有流程的配合

```python
# 管理端 API
@router.post("/courses/{course_id}/optimize")
async def optimize_course(course_id: str, options: OptimizeOptions):
    """
    1. 读取 courses/{course_id}/ 目录
    2. 调用优化 Agent
    3. 覆盖写入优化后的内容
    4. 返回优化报告
    """
    pass

@router.post("/courses/{course_id}/publish")
async def publish_course(course_id: str):
    """
    1. 验证课程内容完整性
    2. 导入到数据库（Course, Chapter）
    3. 生成 Embedding
    4. 设置 is_active=true
    """
    pass
```

---

## 六、实施步骤

### Phase 1：数据模型准备
1. [ ] Chapter 模型添加 `is_active` 字段
2. [ ] Course 模型 `is_active` 默认值改为 `False`
3. [ ] 数据库迁移

### Phase 2：Embedding 系统简化
1. [ ] 移除 `course_local_xxx` / `course_online_xxx` 双数据源
2. [ ] 统一使用 `course_{course_id}` 单一 collection
3. [ ] 删除 sync-to-db、sync-all 同步逻辑
4. [ ] 删除 temp_ref 相关代码
5. [ ] 简化 metadata 结构

### Phase 3：API 调整
1. [ ] Admin API 统一使用 UUID
2. [ ] 添加 `/courses/{id}/publish` 发布接口
3. [ ] C 端查询增加 `is_active=true` 过滤

### Phase 4：课程优化 Agent
1. [ ] 设计 `course_pipeline/optimizer/` 模块
2. [ ] 实现内容润色 Skill
3. [ ] 实现章节重排 Skill
4. [ ] 集成到发布流程

---

## 七、风险评估

### 7.1 简化的风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 本地编辑影响线上检索 | 中 | 发布前不允许生成 embedding |
| 无法回滚已发布内容 | 低 | 软删除 + 保留旧版本 embedding |
| 迁移数据丢失 | 高 | 先备份，再迁移 |

### 7.2 不简化的风险

| 风险 | 影响 |
|------|------|
| 维护成本持续增加 | 高 |
| 新功能难以添加 | 高 |
| Bug 修复复杂度增加 | 中 |

---

## 八、决策待定

1. **课程优化后的内容覆盖方式**
   - 选项 A：直接覆盖 courses/ 目录
   - 选项 B：新建 courses_preview/ 目录，确认后替换

2. **Embedding 重建策略**
   - 选项 A：内容变化后自动重建
   - 选项 B：手动触发重建

3. **现有 local/online 数据迁移**
   - 需要评估现有数据量

---

## 九、参考

- [标识符使用规范](../../docs/identifier_conventions.md)
- [知识库同步功能重构日志](./knowledge_base_sync_refactor_20260221.md)
- [课程 Pipeline 文档](../../src/backend/app/course_pipeline/README.md)
