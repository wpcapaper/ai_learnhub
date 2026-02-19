# Admin Frontend 重构 - Agent 化改造

**日期**: 2026-02-19  
**类型**: 架构重构  
**影响范围**: admin-frontend, app/agent, app/api/admin.py

---

## 一、重构背景

原有 admin-frontend 存在以下问题：
1. **UI 风格不统一**：CLI 终端风格不适合所有场景
2. **缺少 Agent 智能化**：RAG 优化需要人工触发，缺少自动化工作流
3. **无流式输出**：长时间任务无法实时展示进度
4. **LLM 调用未统一**：缺少 Langfuse 监控覆盖

---

## 二、架构方案

### 2.1 Agent 范式选择

经过评估，选择 **Skills-based + 流式输出** 方案：

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|:----:|
| ReAct | 灵活、自适应 | 不可控、可能循环 | ❌ |
| **Skills-based** | 可控、可预测、易调试 | 灵活性较低 | ✅ |
| Plan-and-Execute | 结构清晰 | 规划成本高 | ❌ |
| Tool Chain | 简单高效 | 不够智能 | ❌ |

### 2.2 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Admin Frontend (Next.js 15)                   │
├─────────────────────────────────────────────────────────────────┤
│  课程管理 (现代UI)  │  质量评估 (CLI流式)  │  RAG优化 (CLI流式)  │
│         │                  │                    │                │
│         ▼                  ▼                    ▼                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    SSE 流式输出                          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Agent Framework                       │
├─────────────────────────────────────────────────────────────────┤
│  RAGOptimizerAgent                                              │
│  Skills: analyze_content | test_chunking | evaluate_retrieval   │
│          compare_strategies | generate_summary                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 统一封装 + Langfuse 监控                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、新增文件

### 3.1 后端 Agent 框架 (`app/agent/`)

```
app/agent/
├── __init__.py        # 模块导出
├── base.py            # Agent 基类 + Skills 装饰器
├── events.py          # SSE 事件定义
└── rag_optimizer.py   # RAG 优化 Agent 实现
```

**核心类**：

| 类名 | 功能 |
|------|------|
| `Agent` | Agent 抽象基类 |
| `AgentContext` | 执行上下文 |
| `AgentEvent` | SSE 事件封装 |
| `skill` | Skills 装饰器 |
| `RAGOptimizerAgent` | RAG 优化智能体 |

**RAGOptimizerAgent Skills**：

| Skill | 功能 |
|-------|------|
| `analyze_content` | 分析课程内容特征 |
| `test_chunking` | 测试分块策略 |
| `generate_test_queries` | 生成测试查询 |
| `evaluate_retrieval` | 评估检索效果 |
| `compare_strategies` | 对比策略结果 |
| `generate_summary` | 生成优化摘要（LLM） |

### 3.2 前端页面更新

| 文件 | 变更 |
|------|------|
| `globals.css` | 现代UI样式（dify风格）+ CLI终端样式 |
| `layout.tsx` | 侧边栏导航布局 |
| `page.tsx` | 课程管理页面（卡片式布局） |
| `optimization/page.tsx` | RAG优化工作台（CLI流式输出） |

---

## 四、API 变更

### 4.1 新增 SSE 端点

```http
POST /api/admin/rag/optimize/stream
Content-Type: application/json

{
  "course_id": "llm_basic"
}
```

**响应**: SSE 流式事件

```
data: {"type":"agent_start","content":"开始优化课程..."}
data: {"type":"skill_start","skill":"analyze_content","content":"分析内容特征"}
data: {"type":"skill_output","content":"检测到 6 个章节..."}
data: {"type":"progress","data":{"current":1,"total":4,"percent":25}}
data: {"type":"agent_complete","content":"优化完成","data":{...}}
```

### 4.2 新增 Skills 列表端点

```http
GET /api/admin/agent/skills

Response:
{
  "skills": [
    {"name": "analyze_content", "description": "分析课程内容特征"},
    {"name": "test_chunking", "description": "测试分块策略"},
    ...
  ]
}
```

---

## 五、Langfuse 监控

所有 LLM 调用已接入 Langfuse：

1. **Agent 执行追踪**: 整个 Agent 执行过程被追踪
2. **Skill LLM 调用**: `generate_summary` 使用统一 LLM 封装
3. **Usage 统计**: Token 使用量自动记录

**追踪示例**：
```python
# RAGOptimizerAgent.generate_summary()
from app.llm import get_llm_client
from app.llm.langfuse_wrapper import _get_langfuse_client

langfuse_client = _get_langfuse_client()
if langfuse_client:
    trace = langfuse_client.trace(
        name="rag_optimization_summary",
        tags=["agent", "rag", "summary"],
    )
    # ... LLM 调用 ...
    trace.generation(
        name="llm_summary",
        usage={"input": ..., "output": ..., "total": ...},
    )
```

---

## 六、使用示例

### 6.1 启动优化（CLI 流式输出）

1. 访问 `/optimization` 页面
2. 选择课程
3. 点击"启动优化"
4. 实时查看 Agent 执行过程

**输出示例**：
```
[Agent] 开始 RAG 优化任务...
[Agent] 目标课程: llm_basic
[Skill] analyze_content: 分析内容特征
  → 检测到 6 个章节，含代码块，平均章节 2000 字
[Agent] 根据内容特征，选择测试策略: semantic_medium, fixed_medium, heading_based
[1/3] 测试策略: semantic_medium...
[Skill] test_chunking: 测试分块策略: semantic_medium
  → 生成 45 个分块，平均 450 字
[Skill] evaluate_retrieval: 评估检索效果: semantic_medium
  → 召回率: 82.0%, F1: 78.5%
...
[Agent] ===== 优化完成 =====
[推荐策略] heading_based
heading_based 策略在技术文档场景下表现最佳，预期召回率 85%...
```

### 6.2 自定义 Agent

```python
from app.agent import Agent, AgentContext, skill

class MyAgent(Agent):
    @skill("my_skill", description="自定义技能")
    def my_skill(self, data: str) -> dict:
        return {"result": "processed"}
    
    async def execute(self, context: AgentContext):
        yield AgentEvent.agent_start("Starting...")
        result = await self.call_skill("my_skill", data="test")
        yield AgentEvent.skill_output("my_skill", str(result))
        yield AgentEvent.agent_complete("Done!")
```

---

## 七、验证清单

- [x] Agent 框架导入正常
- [x] RAGOptimizerAgent 6 个 Skills 已注册
- [x] SSE API 端点已添加
- [x] 前端课程管理页面（现代UI）
- [x] 前端 RAG 优化页面（CLI流式）
- [x] LLM 调用统一封装
- [x] Langfuse 监控覆盖
- [x] Tailwind CSS 4 配置修复
- [x] UI 布局和样式优化

---

## 八、UI 优化详情（2026-02-19 更新）

### 8.1 修复 Tailwind CSS 4 配置

**问题**: Tailwind CSS 4 样式未生效，导致页面布局混乱

**原因**: 缺少 `postcss.config.mjs` 配置文件

**修复**: 新增 `src/admin-frontend/postcss.config.mjs`

```javascript
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

### 8.2 布局优化 (`layout.tsx`)

- 侧边栏宽度调整为 240px
- 导航分组：主菜单 / 系统
- Logo 区域添加 hover 发光效果
- 底部添加系统状态指示器（绿色脉冲点）

### 8.3 课程管理页优化 (`page.tsx`)

**新增组件**:
- `StatCard`: 统计卡片，支持图标、渐变背景、高亮状态
- `CourseCard`: 课程卡片，质量分数颜色分级显示
- `EmptyState`: 空状态提示，带渐变图标
- `LoadingSkeleton`: 加载骨架屏

**视觉改进**:
- 面包屑导航
- 质量分数分级颜色（绿/黄/红）
- 卡片 hover 发光效果
- 操作按钮 hover 显示

### 8.4 全局样式优化 (`globals.css`)

**CSS 变量主题**:
```css
:root {
  --background: #09090b;
  --card: #18181b;
  --accent: #8b5cf6;
  --text-primary: #fafafa;
  ...
}
```

**新增样式类**:
- `.sidebar`, `.sidebar-item`, `.sidebar-item.active`
- `.card-glow` 卡片发光效果
- `.metric-card`, `.metric-label`, `.metric-value`
- `.btn-primary`, `.btn-secondary`, `.btn-ghost`
- `.tag-success`, `.tag-warning`, `.tag-error`, `.tag-info`
- `.terminal` CLI 终端样式
- `.line-clamp-2`, `.truncate` 文本截断

---

## 九、后续工作

1. **质量评估页面重构**: 添加 CLI 流式输出（待完成）
2. **系统设置页面**: RAG 配置管理（待完成）
3. **Agent 扩展**: 添加更多 Skills（知识图谱生成等）
4. **前端优化**: 添加结果可视化图表
5. **API 对接**: 前端需要后端 API 支持才能展示实际数据

---

## 十、文件变更清单

### 后端新增文件
- `src/backend/app/agent/__init__.py`
- `src/backend/app/agent/base.py`
- `src/backend/app/agent/events.py`
- `src/backend/app/agent/rag_optimizer.py`

### 前端修改文件
- `src/admin-frontend/app/globals.css` - 全局样式重构
- `src/admin-frontend/app/layout.tsx` - 侧边栏布局
- `src/admin-frontend/app/page.tsx` - 课程管理页面
- `src/admin-frontend/app/optimization/page.tsx` - RAG 优化页面
- `src/admin-frontend/lib/api.ts` - API 客户端

### 前端新增文件
- `src/admin-frontend/postcss.config.mjs` - PostCSS 配置（Tailwind CSS 4 必需）

---

## 十一、启动方式

```bash
# 后端
cd src/backend
uv run uvicorn main:app --reload --port 8000

# 前端
cd src/admin-frontend
npm run dev
# 访问 http://localhost:3002
```

---

## 十二、课程管理 API 实现（2026-02-19 更新）

### 12.1 新增 API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/admin/raw-courses` | GET | 列出原始课程（raw_courses 目录） |
| `/api/admin/database/courses` | GET | 列出数据库中的课程 |
| `/api/admin/courses/import` | POST | 将 courses 目录导入数据库 |
| `/api/admin/database/courses/{id}` | DELETE | 从数据库删除课程（软删除） |
| `/api/admin/quiz/generate` | POST | 基于课程内容生成自测题（预埋） |

### 12.2 Docker 配置更新

**问题**: Docker 容器无法访问 courses 和 raw_courses 目录

**修复**: 更新 `docker-compose.yml` 添加卷挂载

```yaml
services:
  backend:
    volumes:
      - ./src/backend/data:/app/data
      - ./src/backend/app:/app/app
      - ./courses:/app/courses        # 新增
      - ./raw_courses:/app/raw_courses  # 新增
```

**代码适配**: `admin.py` 中添加 Docker 路径检测逻辑

```python
def get_courses_dir() -> Path:
    # 优先使用 Docker 挂载路径
    docker_path = Path("/app/courses")
    if docker_path.exists():
        return docker_path
    # 本地开发：相对于项目根目录
    return Path(__file__).parent.parent.parent.parent.parent / "courses"
```

### 12.3 前端页面重构

**三标签页设计**:
- **原始课程**: 显示 raw_courses 目录内容，支持转换为标准课程
- **已转换**: 显示 courses 目录内容，支持导入数据库
- **已导入**: 显示数据库中的课程，支持删除

**统计卡片**:
- 原始课程数量
- 已转换课程/章节数量
- 已导入课程/章节数量
- 待处理数量

### 12.4 前端 API 客户端新增

```typescript
// 新增类型
export interface RawCourse { id, name, path, file_count, has_content }
export interface DatabaseCourse { id, code, title, description, course_type, is_active, chapter_count, created_at }
export interface ImportResult { success, message, imported_courses, imported_chapters, errors }
export interface QuizGenerateResult { success, message, total_questions, chapters_processed }

// 新增方法
adminApi.getRawCourses()
adminApi.getDatabaseCourses()
adminApi.importCoursesToDatabase()
adminApi.deleteCourseFromDatabase(courseId)
adminApi.generateQuiz(courseId, config?)
```

---

## 十三、题目生成预埋功能（2026-02-19 更新）

### 13.1 现有脚本

发现 `scripts/generate_questions_from_course.py` 脚本：
- 读取 courses/ 目录下的 Markdown 文件
- 使用 AsyncOpenAI 调用 LLM 生成单选题
- 输出 JSON 文件到 scripts/data/output/

**待改进**:
- 使用项目统一的 `get_llm_client` 封装
- 添加 Langfuse 监控
- 集成到后端 API

### 13.2 预埋 API

```http
POST /api/admin/quiz/generate
Content-Type: application/json

{
  "course_id": "python_basics",
  "chapter_count": 5,
  "question_types": ["single_choice", "multiple_choice"],
  "difficulty": "medium"
}

Response:
{
  "success": false,
  "message": "题目生成功能开发中，敬请期待",
  "total_questions": 0,
  "chapters_processed": 3
}
```

### 13.3 前端入口

在课程卡片上添加"生成题目"按钮：
- 点击后调用预埋 API
- 显示处理结果提示框
- 蓝色提示：功能开发中
- 绿色提示：生成成功

---

## 十四、验证清单更新

- [x] Docker 卷挂载配置
- [x] Docker 路径检测逻辑
- [x] 原始课程 API
- [x] 数据库课程 API
- [x] 课程导入 API
- [x] 课程删除 API
- [x] 题目生成预埋 API
- [x] 前端三标签页布局
- [x] 前端统计卡片
- [x] 前端操作按钮
- [x] 前端构建验证

---

## 十五、后续工作更新

1. **题目生成功能实现**: 
   - 改造 `generate_questions_from_course.py` 使用统一 LLM 封装
   - 添加 Langfuse 监控
   - 实现 `/api/admin/quiz/generate` 实际逻辑

2. **质量评估页面重构**: 添加 CLI 流式输出

3. **系统设置页面**: RAG 配置管理

4. **Agent 扩展**: 添加更多 Skills

---

## 十六、流程引导优化（2026-02-19 更新）

### 16.1 问题

点击"转换为课程"按钮后，用户不知道下一步是去"已转换"标签页导入数据库。

### 16.2 解决方案

在操作完成后显示结果提示框，并提供快捷跳转按钮：

**转换完成后**:
- 显示成功/失败状态
- 显示转换数量
- 提供"去导入"按钮，点击后跳转到"已转换"标签页

**导入完成后**:
- 显示成功/失败状态
- 显示导入的课程和章节数量
- 提供"查看已导入"按钮，点击后跳转到"已导入"标签页

---

## 十七、全局字体大小调整（2026-02-19 更新）

### 17.1 问题

用户反馈 admin-frontend 所有页面字体太小，阅读体验不佳。

### 17.2 解决方案

**全局基准字体调整**:
```css
:root {
  --font-size-base: 17px;  /* 从默认 16px 增加到 17px */
}

html {
  font-size: var(--font-size-base);
}
```

**组件字体大小调整**:

| 组件 | 原大小 | 新大小 |
|------|--------|--------|
| 按钮 (.btn) | 13px | 15px |
| 标签 (.tag) | 11px | 13px |
| 终端 (.terminal) | 12px | 14px |
| 指标标签 (.metric-label) | 11px | 13px |
| 指标数值 (.metric-value) | 28px | 36px |
| 侧边栏项 (.sidebar-item) | 13px | 15px |
| 表格标题 | 11px | 13px |
| 表格内容 | 13px | 15px |

**页面组件内联样式调整**:
- text-[10px] → text-[12px]
- text-[11px] → text-[13px]
- text-[14px] → text-[16px]
- text-[15px] → text-[17px]
- text-xs → text-sm
- 侧边栏宽度从 240px 增加到 260px

### 17.3 效果

整体字体放大约 1.25-1.3 倍，阅读体验明显改善。

---

## 十八、单课程转换/导入与资产复制（2026-02-19 更新）

### 18.1 问题

1. 转换按钮只有批量操作，无法单独转换某个课程
2. 导入按钮同理，无法单独导入
3. ipynb 转换包含了 code cell 的输出（执行结果），但这些输出在静态文档中无意义
4. 软删除的课程无法重新导入（检查条件有误）
5. 课程中的图片资源未复制到目标目录

### 18.2 解决方案

**前端优化**:
- 原始课程卡片添加"转换"按钮
- 已转换课程卡片添加"导入"按钮
- 原来的批量按钮文案改为"一键转换所有课程"和"一键导入所有课程"

**后端新增 API**:
```
POST /api/admin/courses/convert/{course_id}  - 转换单个课程
POST /api/admin/courses/import/{course_id}   - 导入单个课程
```

**ipynb 转换优化**:
移除 `_format_code_cell` 中的输出处理逻辑，只保留代码块：
```python
def _format_code_cell(self, code: str, cell: Dict[str, Any], language: str) -> str:
    parts = []
    if code.strip():
        cleaned_code = self._clean_magic_commands(code)
        parts.append(f"```{language}\n{cleaned_code}\n```")
    return '\n'.join(parts)
```

**软删除修复**:
导入时使用 UPSERT 逻辑：
- 存在未删除的同 code 课程 → 报错"已存在"
- 存在已软删除的同 code 课程 → UPDATE 恢复（清除 is_deleted，更新字段，删除旧章节）
- 不存在 → INSERT 新建

```python
existing = db.query(Course).filter(Course.code == course_code).first()

if existing and not existing.is_deleted:
    raise HTTPException(status_code=400, detail="课程代码已存在")

if existing and existing.is_deleted:
    existing.is_deleted = False
    existing.title = course_json.get("title")
    db.query(Chapter).filter(Chapter.course_id == existing.id).delete()
    course = existing
else:
    course = Course(id=str(uuid.uuid4()), code=course_code, ...)
    db.add(course)
```

**资产复制**:
在 `CoursePipeline.convert_course` 中添加 `_copy_assets` 方法，自动复制图片等资源：
```python
def _copy_assets(self, source_dir: str, output_dir: Path) -> int:
    asset_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico', '.pdf', '.zip'}
    # 递归复制所有资源文件，保持目录结构
```

### 18.3 文件变更

| 文件 | 变更 |
|------|------|
| `src/backend/app/api/admin.py` | 新增单课程转换/导入 API，修复软删除检查 |
| `src/backend/app/course_pipeline/converters/__init__.py` | 移除 ipynb 输出处理 |
| `src/backend/app/course_pipeline/pipeline.py` | 添加 `_copy_assets` 资产复制 |
| `src/admin-frontend/lib/api.ts` | 新增 `convertSingleCourse`、`importSingleCourseToDatabase` |
| `src/admin-frontend/app/page.tsx` | 卡片添加单独操作按钮，批量按钮文案更新 |

---

## 十九、课程图片显示修复（2026-02-19 更新）

### 19.1 问题

用户端渲染 markdown 内容时，课程图片无法显示。

**根本原因**：
1. 后端没有提供静态文件服务来访问 courses 目录
2. 前端 MarkdownReader 没有处理相对图片路径

### 19.2 解决方案

**后端静态文件服务**：

在 `main.py` 中挂载 courses 目录：
```python
# Docker 环境中 courses 目录挂载在 /app/courses
courses_path = Path("/app/courses")
if not courses_path.exists():
    # 本地开发环境
    courses_path = Path(__file__).parent.parent.parent.parent / "courses"
if courses_path.exists():
    app.mount("/courses", StaticFiles(directory=str(courses_path)), name="courses")
```

**前端图片路径重写**：

在 MarkdownReader 组件中添加 `rewriteImageUrl` 函数：
```typescript
const rewriteImageUrl = (src: string): string => {
  // 跳过网络图片和绝对路径
  if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('/')) {
    return src;
  }
  // 没有课程信息则返回原路径
  if (!courseCode || !chapterPath) {
    return src;
  }
  // 计算章节所在目录
  const chapterDir = chapterPath.includes('/') ? chapterPath.substring(0, chapterPath.lastIndexOf('/')) : '';
  const basePath = chapterDir ? `${courseCode}/${chapterDir}` : courseCode;
  // 拼接完整 URL
  return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/courses/${basePath}/${src}`;
};
```

**后端 API 增强**：

`LearningService.get_chapter_content` 返回 `course_code` 和 `file_path`：
```python
# 查询课程信息，获取 course.code
course = db.query(Course).filter(Course.id == chapter.course_id).first()
course_code = course.code if course else ""

# 从 course.json 读取章节的文件路径
file_path = ""
if course_code:
    courses_dir = _get_courses_dir()
    course_json_path = courses_dir / course_code / "course.json"
    if course_json_path.exists():
        with open(course_json_path, 'r', encoding='utf-8') as f:
            course_json = json.load(f)
        chapters_info = course_json.get("chapters", [])
        for ch_info in chapters_info:
            if ch_info.get("sort_order") == chapter.sort_order:
                file_path = ch_info.get("file", "")
                break
```

### 19.3 文件变更

| 文件 | 变更 |
|------|------|
| `src/backend/main.py` | 添加 courses 目录静态文件挂载 |
| `src/backend/app/services/learning_service.py` | 返回 course_code 和 file_path |
| `src/frontend/components/MarkdownReader.tsx` | 添加图片路径重写逻辑 |
| `src/frontend/app/learning/page.tsx` | 传递 course_code 和 file_path 参数 |
| `src/frontend/lib/api.ts` | 更新 ChapterContent 类型定义 |

### 19.4 URL 示例

原始 markdown: `![](./assets/gpt-llama2.png)`

转换后 URL: `http://localhost:8000/courses/13.向量工程和RAG系统/课上代码/rag-embeddings/assets/gpt-llama2.png`

### 19.5 course_code 与目录名的区别

**问题**：`course_code`（如 `13_向量工程和rag系统`）与实际目录名（如 `13.向量工程和RAG系统`）可能不同。

**解决**：后端 API 返回 `course_dir_name` 字段，前端使用目录名拼接图片 URL。

```
course_code: 13_向量工程和rag系统  (数据库中的 code，下划线、小写)
course_dir_name: 13.向量工程和RAG系统  (实际目录名，点号、保留大小写)
```
