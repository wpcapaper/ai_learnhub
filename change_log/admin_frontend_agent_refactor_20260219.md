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
