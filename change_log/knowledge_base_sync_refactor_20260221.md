# 知识库同步功能重构 2026-02-21

## 改动意图

### 背景
知识库管理页面存在以下问题：
1. **数据混乱**：本地分块和线上分块存储在同一个 ChromaDB collection 中，导致查询时出现重复数据
2. **同步失败**：一键同步功能显示"同步0个章节，0个文档块"
3. **索引状态不准确**：刷新页面后，章节显示加载状态，无法正确显示索引进度
4. **UI 布局不合理**：状态信息和操作按钮位置混乱

### 目标
1. 本地分块和线上分块完全分离，使用独立的 ChromaDB collection
2. 一键索引和一键同步功能正常工作
3. 索引状态准确显示，刷新页面后状态保持
4. UI 布局清晰，操作流程顺畅

---

## 改动经过

### 阶段一：问题诊断

#### 问题1：索引状态卡在 pending
- **现象**：点击一键索引后，状态显示"已索引 0/3 章节"，所有章节都是加载态
- **原因**：`ChapterKBConfig` 表中状态为 `pending`，但任务实际已完成
- **修复**：清理脏数据，将 `pending` 状态且有 `chunk_count > 0` 的记录改为 `indexed`

#### 问题2：状态更新失败
- **现象**：Worker 执行成功但状态未更新
- **原因**：`index_chapter` 函数优先按 `chapter_id` 字段查询，但传入的参数是 `temp_ref` 格式
- **修复**：改为优先按 `temp_ref` 查询

#### 问题3：同步后查询无结果
- **现象**：同步成功但线上课程查询返回 0 条
- **原因**：查询时使用 `course.code` 构建 collection 名称，但数据存储在用目录名命名的 collection 中
- **修复**：修改查询逻辑，使用目录名查找 collection

---

### 阶段二：数据存储架构重构

#### 旧架构问题
```
单一 collection: course_{course_id}
├── 本地分块 (chapter_id = "temp_ref格式")
└── 线上分块 (chapter_id = "UUID格式")
```
- 本地和线上数据混在一起
- 查询时需要复杂的过滤逻辑
- 容易出现重复数据

#### 新架构设计
```
本地 collection: course_local_{course_code}
└── 本地分块 (chapter_id = "course_code/file.md")

线上 collection: course_online_{course_code}  
└── 线上分块 (chapter_id = "UUID", synced_from = "原temp_ref")
```
- 数据完全隔离
- 查询简单直接
- 便于独立管理

---

### 阶段三：关键代码修改

#### 3.1 后端 - 任务索引 (jobs.py)
```python
# 旧代码
collection_name = normalize_collection_name(f"course_{course_id}")

# 新代码
collection_name = normalize_collection_name(f"course_local_{course_id}")
```

#### 3.2 后端 - 同步 API (admin_kb.py)
```python
# 创建独立的本地和线上 store
local_store = ChromaVectorStore(
    collection_name=normalize_collection_name(f"course_local_{dir_name}"),
    persist_directory=rag_service.persist_directory
)

online_store = ChromaVectorStore(
    collection_name=normalize_collection_name(f"course_online_{dir_name}"),
    persist_directory=rag_service.persist_directory
)

# 从本地读取，写入线上
all_chunks = local_store.get_all_chunks()
# ... 处理 ...
online_store.add_chunks(new_chunks_data, new_embeddings)
```

#### 3.3 后端 - 查询 API (admin_kb.py)
```python
# 本地分块查询
store = ChromaVectorStore(
    collection_name=normalize_collection_name(f"course_local_{course_code}"),
    ...
)

# 线上分块查询  
store = ChromaVectorStore(
    collection_name=normalize_collection_name(f"course_online_{course.code}"),
    ...
)
```

#### 3.4 后端 - RAG 服务 (service.py)
```python
def _get_vector_store(self, course_id: str, source: str = "local") -> ChromaVectorStore:
    collection_name = normalize_collection_name(f"course_{source}_{course_id}")
    return ChromaVectorStore(
        collection_name=collection_name,
        persist_directory=self.persist_directory
    )

def get_retriever(self, course_id: str, source: str = "online") -> RAGRetriever:
    vector_store = self._get_vector_store(course_id, source)
    return RAGRetriever(
        embedding_model=self.embedding_model,
        vector_store=vector_store
    )
```

#### 3.5 前端 - 批量索引 (page.tsx)
```typescript
const handleBatchIndex = async () => {
  // course_id 使用目录名（用于找文件）
  const courseId = selectedCourse.id;
  // temp_ref 使用 course_code（用于唯一标识）
  const courseCode = selectedCourse.code;
  
  const chapters = selectedCourse.chapters.map(ch => ({
    file: ch.file,
    temp_ref: `${courseCode}/${ch.file}`,
    chapter_id: ch.realChapterId
  }));
  
  const res = await adminApi.reindexCourse(courseId, chapters, true);
  // ...
};
```

---

### 阶段四：遇到的坑和解决

#### 坑1：numpy array 真值判断
```python
# 错误写法
if results["embeddings"]:  # ValueError: truth value is ambiguous
    ...

# 正确写法
if embeddings is not None and len(embeddings) > 0:
    ...
```

#### 坑2：course_id vs course_code vs dir_name 混用
- `course_id`：目录名，如 "13.向量工程和RAG系统"
- `course_code`：课程代码，如 "13_向量工程和rag系统"
- `dir_name`：同 course_id

索引任务使用 `course_id`（目录名）来：
1. 找到课程文件
2. 创建 collection

同步 API 需要：
1. 通过 `course_code` 查找数据库课程
2. 找到对应的目录名
3. 使用目录名访问 collection

#### 坑3：前端状态管理
- `selectedCourse.id` 是目录名
- `selectedCourse.code` 是 course_code
- 批量索引时需要正确区分使用

#### 坑4：重复代码删除了中文注释
- 修改代码时不小心删除了中文注释
- 需要保留有价值的注释，只删除不必要的

---

### 阶段五：验证结果

```
索引测试:
  course_local_13.向量工程和RAG系统: 58 chunks
    chapter_id=13.向量工程和RAG系统/00_前言.md

同步测试:
  已同步 3 个章节，共 58 个分块

线上验证:
  course_online_13.向量工程和RAG系统: 58 chunks
    chapter_id=0a0661e9-ac58-427e-b... (UUID)
    synced_from=13.向量工程和RAG系统/00_前言.md
```

---

## 修改的文件清单

### 后端
- `src/backend/app/rag/service.py` - 添加 source 参数支持
- `src/backend/app/rag/vector_store/chroma.py` - 添加 `get_chunks_with_embeddings` 方法
- `src/backend/app/tasks/jobs.py` - 使用 `course_local_` 前缀
- `src/backend/app/api/admin_kb.py` - 大量修改：
  - 同步 API 使用独立 collection
  - 查询 API 使用正确的 collection 名称
  - 召回测试使用本地 collection

### 前端
- `src/admin-frontend/lib/api.ts` - 添加 `syncCourseToOnline` 方法
- `src/admin-frontend/app/knowledge-base/page.tsx` - 修改：
  - 批量索引使用正确的 course_id
  - UI 布局调整
  - 状态管理优化

---

## 后续待办

1. [ ] UI 优化：数据源切换后显示对应章节的分块数量
2. [ ] 添加同步进度显示
3. [ ] 清理旧的 collection 数据
4. [ ] 添加单元测试

---

## 经验总结

1. **命名规范很重要**：course_id、course_code、dir_name 要明确定义和使用
2. **数据隔离**：不同用途的数据应该存储在独立的 collection
3. **numpy 陷阱**：不能直接用 if 判断 numpy array
4. **保留有价值的注释**：修改代码时注意不要误删
5. **先诊断后修复**：通过日志和调试找出根本原因，而不是盲目修改
