# Code Review Report: `lyh_version` → `master`

**日期**: 2026-02-18
**分支**: lyh_version
**审阅者**: AI Assistant

---

## 概览

| 项目 | 数值 |
|------|------|
| 变更文件 | 27 个 |
| 新增行数 | +1,469 |
| 删除行数 | -190 |
| 主要功能 | AI 助手、判题增强、脚本工具 |

---

## 变更文件列表

### 后端文件
- `src/backend/Dockerfile` - 新增 openai, python-dotenv 依赖
- `src/backend/app/api/courses.py` - 课程列表逻辑调整
- `src/backend/app/api/learning.py` - AI 助手接入 DeepSeek
- `src/backend/app/api/quiz.py` - 选项类型支持 list
- `src/backend/app/api/review.py` - 新增 allow_new_round 参数
- `src/backend/app/models/__init__.py` - 新增 Conversation, Message
- `src/backend/app/models/conversation.py` - **新增**: AI 对话模型
- `src/backend/app/services/exam_service.py` - 使用增强判题逻辑
- `src/backend/app/services/learning_service.py` - 新增会话管理方法
- `src/backend/app/services/quiz_service.py` - 新增 is_answer_correct 方法
- `src/backend/main.py` - 加载环境变量
- `src/backend/pyproject.toml` - 新增依赖
- `src/backend/uv.lock` - 依赖锁定更新

### 前端文件
- `src/frontend/app/courses/page.tsx` - 学习类课程支持刷题模式
- `src/frontend/app/mistakes/page.tsx` - 增强选项匹配逻辑
- `src/frontend/app/quiz/page.tsx` - 增强选项渲染和匹配
- `src/frontend/components/AIAssistant.tsx` - 完整的 AI 助手实现
- `src/frontend/components/LaTeXRenderer.tsx` - @ts-ignore 修复
- `src/frontend/components/MarkdownReader.tsx` - 集成 LaTeX 渲染
- `src/frontend/lib/api.ts` - API 参数调整
- `src/frontend/package-lock.json` - 依赖更新

### 脚本文件
- `scripts/batch_import_questions.py` - **新增**: 批量导入脚本
- `scripts/generate_course_from_url.py` - **新增**: URL 生成课程
- `scripts/generate_questions_from_course.py` - **新增**: 课程生成题目
- `scripts/import_questions.py` - 支持 update_existing

### 配置文件
- `.gitignore` - 新增 learning_courses/ 忽略
- `docker-compose.yml` - 开发模式配置调整

---

## 🔴 必须修复的问题

### 1. **后端: 数据库会话生命周期问题** ⚠️ 高风险

**文件**: `src/backend/app/api/learning.py` (lines ~295-334)

```python
async def generate_stream():
    # ...
    try:
        LearningService.save_message(db, conversation_id, "assistant", full_response_content)
    except Exception as db_e:
        print(f"Failed to save AI response: {db_e}")
```

**问题**: 在异步生成器中使用外部的同步 `db` session 是危险的。当 `StreamingResponse` 返回后，原始请求上下文可能已经结束，db session 可能已关闭或处于无效状态。

**修复方案**:
```python
async def generate_stream():
    db_stream = SessionLocal()
    try:
        # ... streaming logic ...
        LearningService.save_message(db_stream, conversation_id, "assistant", full_response_content)
        db_stream.commit()
    finally:
        db_stream.close()
```

---

### 2. **后端: SQL LIKE 通配符未转义** ⚠️ 中风险

**文件**: `scripts/import_questions.py` (lines ~84-87)

```python
potential_matches = db.query(Question).filter(
    Question.course_id == course.id,
    Question.content.like(f"{q_data['content'][:50]}%")
).all()
```

**问题**: `like` 查询中的 `%` 和 `_` 是 SQL 通配符，如果题目内容包含这些字符，可能导致意外匹配。

**修复方案**: 对用户内容进行转义或使用更精确的匹配策略。

---

### 3. **前端: 潜在的内存泄漏** ⚠️ 中风险

**文件**: `src/frontend/components/AIAssistant.tsx` (lines ~106-123)

```tsx
typingIntervalRef.current = setInterval(() => {
  // ...
}, 20);
```

**问题**: 如果 `handleSendMessage` 多次快速调用，旧的 interval 可能未被清理。

**修复方案**:
```tsx
// 在设置新 interval 前先清理旧的
if (typingIntervalRef.current) {
  clearInterval(typingIntervalRef.current);
}
typingIntervalRef.current = setInterval(...);
```

---

## 🟡 建议改进

### 4. **后端: 硬编码的课程代码列表**

**文件**: `scripts/batch_import_questions.py` (lines ~46-52)

```python
known_courses = [
    "agent_development_tutorial",
    "langchain_introduction",
    "rag_system_practical_guide",
    "python_basics"
]
```

**问题**: 硬编码的课程列表难以维护，新增课程需要手动更新。

**建议**: 从数据库动态获取已存在的课程代码。

---

### 5. **前端: 重复的选项渲染逻辑**

**文件**: `src/frontend/app/quiz/page.tsx` 和 `src/frontend/app/mistakes/page.tsx`

同样的数组/对象选项转换逻辑重复出现 3+ 次：

```tsx
(Array.isArray(q.options) ? 
  q.options.map((value: string, index: number) => [String.fromCharCode(65 + index), value]) : 
  Object.entries(q.options).map(...)
)
```

**建议**: 提取为共用工具函数：

```tsx
// utils/options.ts
export function normalizeOptions(options: Record<string, string> | string[] | null): [string, string][] {
  if (!options) return [];
  if (Array.isArray(options)) {
    return options.map((value, index) => [String.fromCharCode(65 + index), value]);
  }
  return Object.entries(options).map(([key, value]) => {
    if (/^\d+$/.test(key)) return [String.fromCharCode(65 + parseInt(key)), value];
    return [key, value];
  });
}
```

---

### 6. **后端: API 参数变更未保持向后兼容**

**文件**: `src/backend/app/api/review.py` 和 `src/frontend/lib/api.ts`

```python
# 旧 API: course_type
/api/review/next?user_id=xxx&course_type=exam

# 新 API: course_id  
/api/review/next?user_id=xxx&course_id=xxx
```

**问题**: 如果有外部调用方或缓存的客户端代码，可能导致 400 错误。

**建议**: 考虑同时支持两种参数一段时间，或在响应中添加弃用警告。

---

### 7. **前端: console.log 残留**

**文件**: `src/frontend/app/quiz/page.tsx` (lines ~217-218)

```tsx
console.log('Checking new batch availability...', { userId, courseId });
const nextQuestions = await apiClient.getNextQuestions(userId, courseId, 1, false);
console.log('Next questions check result:', nextQuestions);
```

**建议**: 生产代码应移除或使用条件化的日志。

---

### 8. **后端: 缺少错误处理和重试机制**

**文件**: `scripts/generate_course_from_url.py` (lines ~78-88)

```python
async def fetch_url_content(url: str) -> str:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return clean_html(response.text)
```

**问题**: 对外部 URL 的请求缺少重试机制和更详细的错误信息。

**建议**: 添加重试装饰器或使用 `tenacity` 库。

---

## 🟢 优秀实现

### 9. **判题增强逻辑设计良好**

**文件**: `src/backend/app/services/quiz_service.py` (lines ~135-190)

`is_answer_correct` 方法设计周全：
- ✅ 支持大小写归一化
- ✅ 支持多选题集合匹配（无序）
- ✅ 兼容旧数据（选项内容匹配）
- ✅ 清晰的注释说明

---

### 10. **AI 助手打字机效果实现巧妙**

**文件**: `src/frontend/components/AIAssistant.tsx**

使用 `targetContentRef` 和 `currentDisplayedContentRef` 双缓冲实现平滑的打字机效果，避免了直接操作 DOM。

---

### 11. **对话持久化设计合理**

**文件**: `src/backend/app/models/conversation.py**

- ✅ 独立的 Conversation 和 Message 模型
- ✅ 支持会话摘要（预留字段）
- ✅ Token 消耗统计（预留字段）
- ✅ 用户反馈功能（rating 字段）

---

## 其他观察

### Docker 配置变更

**文件**: `docker-compose.yml`

- Frontend 从构建镜像改为直接挂载源码 + node 镜像（开发模式）
- Backend 新增 env_file 支持
- **注意**: 这更适合开发环境，生产环境应恢复构建模式

### 新增依赖

```
openai>=1.0.0
python-dotenv>=1.0.0
```

---

## 总结建议

| 优先级 | 数量 | 说明 |
|--------|------|------|
| 🔴 必须修复 | 3 | 数据库会话、SQL通配符、内存泄漏 |
| 🟡 建议改进 | 5 | 代码重复、向后兼容、日志清理等 |
| 🟢 优秀实现 | 3 | 判题逻辑、打字机效果、数据模型 |

**建议**: 修复 🔴 问题后再合并到 master。整体代码质量良好，功能实现完整。

---

## 修复跟踪

| 问题 | 状态 | 修复分支 |
|------|------|----------|
| 数据库会话生命周期 | ✅ 已修复 | lyh_version_improve |
| SQL LIKE 通配符 | ✅ 已修复 | lyh_version_improve |
| 前端内存泄漏 | ✅ 已修复 | lyh_version_improve |

---

## 修复详情

### 1. 数据库会话生命周期问题 (learning.py)

**修复方案**:
- 在 `generate_stream()` 异步生成器内部创建独立的数据库会话 `SessionLocal()`
- 使用 `try/finally` 确保会话正确关闭
- 移除了对传入 `db` 参数的依赖

### 2. SQL LIKE 通配符问题 (import_questions.py)

**修复方案**:
- 新增 `escape_like_pattern()` 函数转义 `%` 和 `_` 通配符
- 使用 SQLAlchemy 的 `escape='\\'` 参数指定转义字符
- 保持原有模糊匹配逻辑不变

### 3. 前端内存泄漏问题 (AIAssistant.tsx)

**修复方案**:
- 新增 `useEffect` 清理函数，在组件卸载时清理定时器
- 在设置新定时器前，先清理旧的定时器
- 初始化 `targetContentRef` 和 `currentDisplayedContentRef`
