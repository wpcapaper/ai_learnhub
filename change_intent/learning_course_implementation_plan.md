# 学习课程系统实现计划

## 任务概述

基于目前代码架构，继续实现 learning 类型的课程实现。

## 具体需求

1. **学习课程类型**：基于 markdown 文件的在线学习系统
2. **章节选择**：用户点击对应课程后，可以基于 markdown 选择章节
3. **课程详情页面**：左侧为 markdown 阅读器，右侧为对话式智能助手
4. **AI 助手**：暂时预埋，使用固定回复"阿巴阿巴"的函数，注意使用 openai 的流式协议
5. **进度记忆**：要求可以记忆用户学习的进度，每个章节的访问情况
6. **阅读位置感知**：可以感知到用户当前正在阅读 markdown 的哪个部分，便于 agent 分析
7. **课程存储**：课程 markdown 存储在 /courses 目录，注意这个目录需要 gitignore，可以自行构造样例课程和文本做测试
8. **文档编写**：评估整体需求后，在 change_intent 目录写计划文档，修改后在 change_log 目录写修改日志
9. **代码注释**：注意核心业务逻辑必须有中文注释

## 现有架构分析

### 后端架构
- **框架**：FastAPI + SQLAlchemy
- **数据库**：SQLite（开发环境）/ PostgreSQL（生产环境）
- **结构**：models → services → api 清晰分层
- **Course 模型**：已支持 `course_type` 字段，值为 'exam' | 'learning'

### 前端架构
- **框架**：Next.js 16 (App Router) + React 19 + TypeScript
- **样式**：Tailwind CSS 4
- **状态管理**：React Context API

### 待实现功能
- ❌ 章节模型
- ❌ 阅读进度追踪
- ❌ Markdown 阅读器
- ❌ AI 助手集成（流式协议）
- ❌ /courses 目录及 gitignore
- ❌ 学习课程数据导入

## 实施计划

### 第一阶段：后端数据层

#### 1.1 创建数据库模型

**文件：`src/backend/app/models/chapter.py`**
```python
# 章节模型，存储学习课程的章节信息
class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'))
    title = Column(String(200))
    content_markdown = Column(Text)  # Markdown 内容
    sort_order = Column(Integer)  # 章节排序
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
```

**文件：`src/backend/app/models/reading_progress.py`**
```python
# 阅读进度模型，记录用户阅读进度
class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    chapter_id = Column(String(36), ForeignKey('chapters.id'))
    last_position = Column(Integer, default=0)  # 阅读位置（字符偏移量）
    last_percentage = Column(Float, default=0.0)  # 阅读百分比
    is_completed = Column(Boolean, default=False)  # 是否完成
    last_read_at = Column(DateTime, default=datetime.utcnow)  # 最后阅读时间
    total_read_time = Column(Integer, default=0)  # 总阅读时长（秒）
```

#### 1.2 创建学习服务

**文件：`src/backend/app/services/learning_service.py`**

核心方法：
- `get_chapters(db, course_id)` - 获取课程章节列表
- `get_chapter_content(db, user_id, chapter_id)` - 获取章节内容及用户进度
- `update_reading_progress(db, user_id, chapter_id, position, percentage)` - 更新阅读进度
- `mark_chapter_completed(db, user_id, chapter_id)` - 标记章节完成
- `get_user_progress_summary(db, user_id, course_id)` - 获取用户课程进度摘要

#### 1.3 创建学习 API

**文件：`src/backend/app/api/learning.py`**

端点：
- `GET /api/learning/{course_id}/chapters` - 获取课程章节列表
- `GET /api/learning/{chapter_id}/content` - 获取章节内容
- `POST /api/learning/{chapter_id}/progress` - 更新阅读进度
- `POST /api/learning/{chapter_id}/complete` - 标记章节完成
- `GET /api/learning/{course_id}/progress` - 获取用户课程进度
- `POST /api/learning/ai/chat` - AI 对话接口（流式响应，返回固定"阿巴阿巴"）

#### 1.4 注册路由

**修改文件：`src/backend/main.py`**
```python
from app.api import learning
app.include_router(learning.router, prefix="/api", tags=["学习课程"])
```

### 第二阶段：数据准备

#### 2.1 创建 /courses 目录

```bash
mkdir -p /courses
```

#### 2.2 更新 .gitignore

在项目根目录 .gitignore 中添加：
```
/courses/
```

#### 2.3 创建示例学习课程

**目录结构：**
```
/courses/
└── python_basics/
    ├── course.json
    ├── 01_introduction.md
    ├── 02_variables.md
    └── 03_functions.md
```

**course.json 示例：**
```json
{
  "code": "python_basics",
  "title": "Python 基础入门",
  "description": "学习 Python 编程语言的基础知识",
  "course_type": "learning",
  "cover_image": "https://...",
  "chapters": [
    {
      "title": "Python 简介",
      "file": "01_introduction.md",
      "sort_order": 1
    },
    {
      "title": "变量与数据类型",
      "file": "02_variables.md",
      "sort_order": 2
    },
    {
      "title": "函数定义",
      "file": "03_functions.md",
      "sort_order": 3
    }
  ]
}
```

#### 2.4 创建数据导入脚本

**文件：`scripts/import_learning_courses.py`**

功能：
- 扫描 /courses 目录
- 读取 course.json 和 markdown 文件
- 在数据库中创建学习课程
- 导入章节内容

### 第三阶段：前端实现

#### 3.1 安装依赖

```bash
cd src/frontend
npm install react-markdown remark-gfm react-syntax-highlighter
npm install --save-dev @types/react-syntax-highlighter
```

#### 3.2 创建学习阅读页面

**文件：`src/frontend/app/learning/page.tsx`**

功能：
- 从 URL 参数获取 course_id 和 chapter_id
- 左侧显示 Markdown 阅读器
- 右侧显示 AI 助手
- 侧边栏显示章节导航
- 跟踪阅读进度并同步到后端

#### 3.3 创建组件

**文件：`src/frontend/components/MarkdownReader.tsx`**
- 渲染 Markdown 内容
- 代码语法高亮
- 滚动位置追踪

**文件：`src/frontend/components/ChapterNavigation.tsx`**
- 显示章节列表
- 高亮当前章节
- 显示阅读进度

**文件：`src/frontend/components/AIAssistant.tsx`**
- 聊天界面
- 流式响应显示
- 当前章节上下文

#### 3.4 更新课程页面

**修改文件：`src/frontend/app/courses/page.tsx`**
- 为 learning 类型课程添加"开始学习"按钮
- 点击后跳转到 /learning?course_id=xxx

#### 3.5 更新 API 客户端

**修改文件：`src/frontend/lib/api.ts`**

添加方法：
- `getLearningChapters(courseId)` - 获取章节列表
- `getChapterContent(chapterId, userId)` - 获取章节内容
- `updateReadingProgress(chapterId, userId, progress)` - 更新进度
- `markChapterCompleted(chapterId, userId)` - 标记完成
- `getLearningProgress(courseId, userId)` - 获取进度
- `aiChatStream(chapterId, message)` - AI 对话（流式）

### 第四阶段：AI 助手实现（预埋）

#### 4.1 后端流式响应

在 `app/api/learning.py` 中实现流式响应端点：
```python
from fastapi.responses import StreamingResponse

@router.post("/learning/ai/chat")
async def ai_chat(request: ChatRequest):
    """AI 对话接口（流式响应，返回固定"阿巴阿巴"）"""

    async def generate_stream():
        response_text = "阿巴阿巴"
        # 模拟流式输出
        for char in response_text:
            yield char
            await asyncio.sleep(0.05)

    return StreamingResponse(generate_stream(), media_type="text/plain")
```

#### 4.2 前端流式读取

在 `AIAssistant.tsx` 中使用 ReadableStream 读取流式响应。

## 实施步骤

### Wave 1: 后端核心（并行）
1. 创建 Chapter 模型
2. 创建 ReadingProgress 模型
3. 创建 LearningService
4. 创建学习 API 端点
5. 注册路由

### Wave 2: 数据准备（依赖 Wave 1）
1. 创建 /courses 目录
2. 更新 .gitignore
3. 创建示例课程 markdown 文件
4. 创建数据导入脚本
5. 执行导入脚本

### Wave 3: 前端基础（依赖 Wave 1）
1. 安装 react-markdown 等依赖
2. 创建 MarkdownReader 组件
3. 创建 ChapterNavigation 组件
4. 创建学习阅读页面框架
5. 更新 API 客户端

### Wave 4: 前端集成（依赖 Wave 2, 3）
1. 创建 AIAssistant 组件（流式响应）
2. 实现阅读进度追踪
3. 实现滚动位置检测
4. 更新课程页面处理 learning 类型
5. 完整流程测试

### Wave 5: 文档（依赖 Wave 4）
1. 创建计划文档
2. 创建修改日志
3. 验证所有功能

## 文件清单

### 后端文件
- `src/backend/app/models/chapter.py` - 新增
- `src/backend/app/models/reading_progress.py` - 新增
- `src/backend/app/models/__init__.py` - 修改（导入新模型）
- `src/backend/app/services/learning_service.py` - 新增
- `src/backend/app/api/learning.py` - 新增
- `src/backend/main.py` - 修改（注册路由）

### 数据文件
- `/courses/python_basics/course.json` - 新增
- `/courses/python_basics/01_introduction.md` - 新增
- `/courses/python_basics/02_variables.md` - 新增
- `/courses/python_basics/03_functions.md` - 新增
- `.gitignore` - 修改（添加 /courses/）
- `scripts/import_learning_courses.py` - 新增

### 前端文件
- `src/frontend/app/learning/page.tsx` - 新增
- `src/frontend/components/MarkdownReader.tsx` - 新增
- `src/frontend/components/ChapterNavigation.tsx` - 新增
- `src/frontend/components/AIAssistant.tsx` - 新增
- `src/frontend/app/courses/page.tsx` - 修改
- `src/frontend/lib/api.ts` - 修改

### 文档文件
- `change_intent/learning_course_implementation_plan.md` - 新增（本文档）
- `change_log/learning_course_implementation.md` - 新增

## 中文注释要求

所有核心业务逻辑方法必须包含中文注释，包括：
- 方法功能描述
- 参数说明
- 返回值说明
- 关键逻辑说明

示例：
```python
@staticmethod
def get_chapters(db: Session, course_id: str) -> List[Chapter]:
    """
    获取指定课程的所有章节列表

    Args:
        db: 数据库会话
        course_id: 课程 ID

    Returns:
        List[Chapter]: 按排序顺序排列的章节列表

    Raises:
        ValueError: 当课程不存在时抛出异常
    """
    # 查询课程
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError(f"课程 {course_id} 不存在")

    # 查询章节并按排序顺序返回
    chapters = db.query(Chapter).filter(
        Chapter.course_id == course_id,
        Chapter.is_deleted == False
    ).order_by(Chapter.sort_order.asc()).all()

    return chapters
```

## 验收标准

### 功能验收
1. ✅ 可以创建 learning 类型的课程
2. ✅ 可以查看课程章节列表
3. ✅ 可以阅读章节 markdown 内容
4. ✅ 阅读器支持代码语法高亮
5. ✅ AI 助手可以响应（返回"阿巴阿巴"）
6. ✅ 可以切换章节
7. ✅ 阅读进度自动保存
8. ✅ 可以查看课程学习进度

### 技术验收
1. ✅ 所有核心业务逻辑有中文注释
2. ✅ /courses 目录已添加到 .gitignore
3. ✅ AI 助手使用流式协议
4. ✅ 前端响应式布局正常
5. ✅ API 端点有文档说明

## 风险与注意事项

1. **Markdown 文件路径**：确保 /courses 目录路径正确，导入脚本能正确读取
2. **数据库迁移**：新增表需要执行数据库初始化或迁移
3. **流式响应**：确保前端的流式读取与后端的流式输出匹配
4. **进度追踪**：滚动位置和进度百分比的计算要准确
5. **并发处理**：多个用户同时学习时，进度更新不应冲突

## 后续扩展

1. 实现真正的 AI 助手（集成 OpenAI/DeepSeek API）
2. 添加词云可视化
3. 添加知识图谱
4. 实现基于内容的题目生成
5. 添加学习路径推荐

---

**文档版本**：1.0
**创建日期**：2026-02-04
**状态**：待实施
