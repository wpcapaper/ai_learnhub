# RAG 文档块版本控制与召回问题排查解决

**日期**: 2026-02-21
**类型**: 问题排查与功能增强
**影响范围**: RAG 知识库管理、向量存储、前端交互

---

## 问题概述

在开发 RAG 知识库管理功能过程中，遇到以下问题：
1. 召回测试无结果返回
2. 数据污染导致召回重复文本块
3. 缺少版本控制机制防止历史脏数据
4. 前端交互体验问题（alert 强刷、缺少数据源切换等）

---

## 问题一：循环导入导致后端启动失败

### 现象
```
ImportError: cannot import name 'CURRENT_STRATEGY_VERSION' from partially initialized module
```

### 根因
- `strategies.py` 导入 `metadata.py`
- `metadata.py` 导入 `strategies.py` 中的 `CURRENT_STRATEGY_VERSION`
- 形成循环依赖

### 解决方案
创建独立的 `version.py` 文件存放版本常量：

```
version.py ← strategies.py
           ← metadata.py
           ← chroma.py
```

### 修改文件
- 新增: `src/backend/app/rag/chunking/version.py`
- 修改: `src/backend/app/rag/chunking/strategies.py`
- 修改: `src/backend/app/rag/chunking/metadata.py`

---

## 问题二：召回测试无结果

### 现象
在 RAG 课程中提问"什么时候使用RAG"，返回空结果。

### 排查过程

1. **检查 ChromaDB 数据**
   - 确认 collection 存在且有数据（58 chunks）

2. **检查 metadata 结构**
   ```
   chapter_id: course_13._____RAG___0  ← 错误！
   source_file: 13.向量工程和RAG系统/课上代码/rag_tutorial_improved.md
   ```

3. **发现根因**
   - `jobs.py` 第 388 行将 `chapter_id` 设置为 `collection_name`（课程级别）
   - 召回 API 按章节过滤时，使用 `chapter_file in chapter_id` 判断
   - 导致过滤失效

### 解决方案

**修复 1**: 修正 `chapter_id` 存储值
```python
# jobs.py
chunk_count = asyncio.run(rag_service.index_course_content(
    ...
    chapter_id=source_file,  # 使用 source_file 作为章节标识
    ...
))
```

**修复 2**: 召回改为课程级别搜索
```python
# admin_kb.py - 移除章节过滤
# 原因：召回测试应显示整个课程中最相关的结果
results = store.search(
    query_embedding=query_embedding,
    top_k=top_k
)
# 不再按章节过滤
```

### 修改文件
- `src/backend/app/tasks/jobs.py`
- `src/backend/app/api/admin_kb.py`

---

## 问题三：数据污染 - 重复文本块

### 现象
召回结果中出现重复的文本块，查询"什么时候适合用RAG?"返回 5 个结果中有 2-3 个内容相同。

### 排查过程

```python
# 检查 ChromaDB 中的重复数据
content_counter = Counter(results['documents'])
duplicates = {k: v for k, v in content_counter.items() if v > 1}
# 发现 47 个重复的文档块，共 105 chunks（正常应为 58）
```

### 根因
多次执行索引任务时，未正确清理旧数据，导致同一内容被多次写入。

### 解决方案

1. **清理重复数据**
```python
# 按内容分组，保留第一个，删除其余
content_to_ids = defaultdict(list)
for i, doc in enumerate(results['documents']):
    content_to_ids[doc].append(results['ids'][i])

ids_to_delete = []
for content, ids in content_to_ids.items():
    if len(ids) > 1:
        ids_to_delete.extend(ids[1:])

collection.delete(ids=ids_to_delete)
```

2. **版本控制机制**（防止未来污染）
```python
# metadata 中添加版本字段
{
    "strategy_version": "markdown-v1.0",
    "indexed_at": "2026-02-21T15:00:00Z",
}

# 索引流程
1. 获取该章节的旧版本 chunk IDs
2. 写入新版本 chunks
3. 成功后删除旧版本 chunks
```

### 修改文件
- `src/backend/app/rag/chunking/version.py` (新增)
- `src/backend/app/rag/chunking/strategies.py`
- `src/backend/app/rag/chunking/metadata.py`
- `src/backend/app/rag/vector_store/chroma.py`
- `src/backend/app/tasks/jobs.py`

---

## 问题四：前端交互体验问题

### 现象
1. 数据源切换入口不可见
2. 重建索引使用 alert 弹窗强刷页面
3. 召回结果无法查看全文
4. 跨章节召回结果无视觉提示

### 解决方案

**1. 数据源切换始终显示**
```tsx
// 始终显示切换按钮，未导入时禁用数据库选项
<button
  onClick={() => selectedChapter?.realChapterId && setUseTempRef(false)}
  disabled={!selectedChapter?.realChapterId}
  className={...}
>
  数据库
  {!selectedChapter?.realChapterId && <span>(未导入)</span>}
</button>
```

**2. 重建索引改为异步流程**
```tsx
// 轮询任务状态
const pollReindexTask = useCallback(async (taskId: string) => {
  const res = await adminApi.getTaskStatus(taskId);
  if (res.data?.status === 'finished') {
    setReindexing(false);
    loadChunks(true);  // 自动刷新数据
  }
}, []);

// 点击重建后启动轮询
setReindexing(true);
reindexPollingRef.current = setInterval(() => pollReindexTask(taskId), 2000);
```

**3. 召回结果点击显示全文**
```tsx
// 卡片点击打开弹窗
<div onClick={() => setSelectedResult(result)}>
  <div className="line-clamp-3">{result.content}</div>
</div>

// 全文弹窗
{selectedResult && (
  <Modal>
    <pre>{selectedResult.content}</pre>
  </Modal>
)}
```

**4. 跨章节视觉提示**
```tsx
const isFromOtherChapter = (source: string) => {
  const sourceFile = source.split('/').pop();
  return sourceFile !== currentChapterFile;
};

// 显示跨章节标签和特殊背景
{isOtherChapter && (
  <span className="bg-amber-500/20 text-amber-400">跨章节</span>
)}
<div className={isOtherChapter ? 'border-amber-500/30 bg-amber-500/5' : ''}>
```

### 修改文件
- `src/admin-frontend/app/knowledge-base/page.tsx`

---

## 版本控制机制设计

### 元数据字段
```python
{
    "course_id": "python_basics",
    "chapter_id": "python_basics/01_introduction.md",
    "source_file": "python_basics/01_introduction.md",
    "position": 0,
    "content_type": "paragraph",
    "char_count": 790,
    "estimated_tokens": 395,
    "token_level": "normal",
    "strategy_version": "markdown-v1.0",  # 分块策略版本
    "indexed_at": "2026-02-21T07:00:00Z",  # 索引时间
}
```

### 版本号格式
```
{策略类型}-v{major}.{minor}

示例：markdown-v1.0
- major: 不兼容变更（如完全重写分块逻辑）
- minor: 兼容性改进（如调整参数、修复边界情况）
```

### 升级流程
```
1. 修改 CHUNK_STRATEGY_VERSION 常量
2. 清空 ChromaDB（功能未上线，可激进操作）
3. 重建索引
```

---

## 验证结果

### 召回测试
```
查询: "什么时候适合用RAG?"
结果数: 5
耗时: 336.6ms

1. score=0.551  source: 00_前言.md
2. score=0.520  source: rag_tutorial_improved.md
3. score=0.520  source: rag_tutorial_improved.md
4. score=0.517  source: rag_tutorial_improved.md
5. score=0.505  source: 00_前言.md
```

### 数据清理
```
清理前: 105 chunks
清理后: 58 chunks
重复数据: 47 个
```

---

## 待完成

1. **同步到数据库按钮** - 在 tempRef 模式下，已导入课程显示"同步到数据库"按钮
2. **召回测试区分数据源** - 支持从本地 ChromaDB 或数据库召回
3. **API 返回全文** - 召回结果返回完整内容而非截断

---

## 相关文件

### 后端
- `src/backend/app/rag/chunking/version.py` - 版本常量
- `src/backend/app/rag/chunking/strategies.py` - 分块策略
- `src/backend/app/rag/chunking/metadata.py` - 元数据提取
- `src/backend/app/rag/vector_store/chroma.py` - 向量存储
- `src/backend/app/tasks/jobs.py` - 索引任务
- `src/backend/app/api/admin_kb.py` - KB 管理 API

### 前端
- `src/admin-frontend/app/knowledge-base/page.tsx` - 知识库管理页面

### 文档
- `docs/chunking-system.md` - 分块系统说明
