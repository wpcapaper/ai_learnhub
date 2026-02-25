# AILearn Hub

> 基于艾宾浩斯遗忘曲线的 AI 智能学习系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)

## 📖 项目简介

AILearn Hub 是一套基于艾宾浩斯遗忘曲线的 AI 智能学习系统，融合 **RAG（检索增强生成）** 与 **Agent 框架**，实现从课程内容导入、知识库构建到学习/复习闭环的全流程能力。

系统采用 **FastAPI + Next.js** 的前后端分离架构，支持流式交互、异步任务与可观测性监控，面向真实学习场景提供可扩展的工程化落地方案。

### ✨ 核心特性

- **🧠 智能复习调度**
  - 基于艾宾浩斯遗忘曲线的 9 阶段复习算法
  - 自动安排最佳复习时间点，强化记忆效果
  - 答对推进、答错回退的动态调整机制

- **📝 灵活的学习模式**
  - **刷题模式**：批次刷题，实时反馈，支持跳过题目
  - **考试模式**：模拟真实考试环境，支持固定题集和动态抽取
  - **复习模式**：智能推荐待复习题目，针对性巩固薄弱环节
  - **错题本**：自动记录错题，支持一键重练

- **📊 RAG 检索增强生成**
  - 基于 ChromaDB 的向量检索体系
  - 语义切分、多 Embedding 模型适配（OpenAI/BGE/E5）
  - Rerank 重排序与混合检索（向量+关键词）
  - 知识库版本化 Collection 管理，支持无缝更新与回滚
  - 稳定 Chunk ID 机制，保障幂等索引与数据一致性

- **🎯 多课程多题集支持**
  - 灵活的课程管理体系
  - 支持自定义题集（普通题集、固定考试题集）
  - 难度分级、知识点标记等高级功能

- **📥 便捷的数据导入**
  - 支持 Markdown 格式题库导入
  - 支持 Word 文档导入（带红色答案标记）
  - 自动转换为标准 JSON 格式
  - 完整的数据校验和转换报告

- **🔧 开发者友好**
  - Dev 模式免注册快速体验
  - 完整的 RESTful API 文档
  - Docker 一键部署
  - 前后端分离架构
- **🤖 Agent 框架**
  - 基于 Skills 装饰器的 Agent 注册机制
  - SSE 流式输出，增强交互体验
  - RAG Optimizer Agent 课程质量评估

- **📈 可观测性**
  - Langfuse LLM 调用监控与链路追踪
  - Redis Queue 异步任务处理
  - Admin API IP 白名单保护

## 🏗️ 技术架构

### 后端技术栈

- **FastAPI**: 现代、高性能的 Web 框架
  - 自动生成 OpenAPI 文档
  - 类型验证（Pydantic）
  - 异步支持
- **SQLAlchemy**: Python ORM
- **数据库**: SQLite（开发环境）/ PostgreSQL（生产环境）
- **Redis Queue**: 异步任务队列
- **Python**: 3.11+

### 前端技术栈

- **Next.js 16**: React 框架（App Router）
  - 服务端渲染（SSR）
  - 自动代码分割
  - 文件系统路由
- **React 19**: UI 库
- **TypeScript**: 类型安全
- **Tailwind CSS 4**: 原子化 CSS
- **Magic UI**: 现代组件库
- **KaTeX**: 数学公式渲染

### RAG / AI 技术栈

- **ChromaDB**: 向量数据库
- **Embedding**: OpenAI / BGE / E5 多模型支持
- **Semantic Chunking**: 语义切分策略
- **Rerank**: 重排序优化
- **Hybrid Retrieval**: 混合检索（向量+关键词）

### Agent / 交互

- **Skills-based Agent**: 装饰器注册机制
- **SSE**: 流式输出

### 可观测性

- **Langfuse**: LLM 调用监控与链路追踪

### 部署

- **Docker Compose**: 6 服务一键部署（backend, worker, frontend, admin-frontend, redis, langfuse）
## 📁 项目结构

```
aie55_llm5_learnhub/
├── src/
│   ├── backend/                 # 后端服务（FastAPI）
│   │   ├── main.py             # 应用入口
│   │   ├── app/
│   │   │   ├── core/           # 核心模块（数据库、艾宾浩斯算法）
│   │   │   ├── models/         # 数据模型（14+ SQLAlchemy 模型）
│   │   │   ├── services/       # 业务逻辑（9+ Service 层）
│   │   │   ├── api/            # API 路由（16+ 端点）
│   │   │   ├── rag/            # RAG 系统（6 子模块）
│   │   │   │   ├── chunking/   # 语义切分
│   │   │   │   ├── embedding/  # Embedding 模型
│   │   │   │   ├── vector_store/ # ChromaDB 向量存储
│   │   │   │   ├── retrieval/  # 检索器、Rerank
│   │   │   │   ├── evaluation/ # 召回测试
│   │   │   │   └── multilingual/ # 多语言支持
│   │   │   ├── agent/          # Agent 框架
│   │   │   ├── llm/            # LLM 封装层
│   │   │   └── tasks/          # 异步任务
│   │   ├── data/               # 数据库文件
│   │   └── Dockerfile
│   │
│   ├── frontend/               # 前端应用（Next.js）
│   │   ├── app/                # 页面目录（7+ 页面）
│   │   │   ├── page.tsx        # 首页
│   │   │   ├── quiz/           # 刷题页面
│   │   │   ├── exam/           # 考试页面
│   │   │   ├── mistakes/       # 错题本页面
│   │   │   ├── learning/       # 学习页面（Markdown 阅读器）
│   │   │   └── courses/        # 课程页面
│   │   ├── components/         # 可复用组件（10+）
│   │   ├── lib/                # 工具库（API Client）
│   │   └── Dockerfile
│   │
│   └── admin-frontend/         # 管理端应用（Next.js）
│       ├── app/
│       │   ├── page.tsx        # 管理首页
│       │   ├── knowledge-base/ # 知识库管理
│       │   ├── optimization/   # 课程优化
│       │   └── rag-expert/     # RAG 专家
│       └── components/
│
├── scripts/                    # 数据导入脚本
│   ├── init_db.py             # 初始化数据库
│   ├── init_course_data.py    # 初始化课程数据
│   ├── import_questions.py    # 导入题目
│   └── course_pipeline/       # 课程转换管道
│
├── markdown_courses/          # Markdown 课程内容
├── schema.sql                  # 数据库结构定义
├── docker-compose.yml          # Docker Compose 配置（6 服务）
├── RAG_ARCHITECTURE.md        # RAG 架构设计文档
├── PROJECT_HIGHLIGHTS.md      # 项目亮点（简历专用）
├── SCRIPT_MANUAL.md           # 脚本使用手册
└── README.md                  # 项目说明（本文件）
```

## 🚀 快速开始

> ⚠️ **重要提示**：在启动应用之前，必须先运行脚本初始化数据库和导入数据！
> 详细步骤请参考下方的"初始化数据"部分。

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/yourusername/aie55_llm5_learnhub.git
cd aie55_llm5_learnhub

# 配置环境变量（可选，修改端口等）
cp .env.example .env
# 编辑 .env 文件修改端口配置

# 启动所有服务
docker-compose up -d

# 访问应用（默认端口）
# 前端 (C端)：http://localhost:3000
# 管理端：http://localhost:8080
# 后端 API：http://localhost:8000
# API 文档：http://localhost:8000/docs
# LLM 监控：http://localhost:9090
```

### 方式二：本地开发

#### 1. 后端启动

```bash
# 进入后端目录
cd src/backend

# 安装依赖（使用 uv）
# 如果未安装 uv，先运行: pip install uv
uv sync

# 启动开发服务器
uv run uvicorn main:app --host 0.0.0.0 --reload --port 8000
```

后端服务将在 `http://localhost:8000` 启动

#### 2. 前端启动

```bash
# 进入前端目录
cd src/frontend

# 安装依赖
npm install

# 配置环境变量（创建 .env.local）
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 启动开发服务器
npm run dev
```

前端应用将在 `http://localhost:3000` 启动

#### 3. ⚠️ 初始化数据（必须执行）

> **重要**：在启动应用之前，必须执行以下步骤初始化数据库和创建课程数据，否则应用无法正常运行！

```bash
# 进入脚本目录
cd scripts

# 安装依赖
uv sync

# 步骤 1: 初始化数据库表结构
uv run python init_db.py

# 步骤 2: 创建默认课程数据
uv run python init_course_data.py

# 步骤 3: 导入题目数据（必需，否则无法开始学习）
uv run python import_questions.py --json-file sample_quiz.json --course-code llm_basic
```

**验证**：执行完以上步骤后，如果看到类似"导入完成！总题目数: 99"的输出，说明初始化成功。

详细脚本使用说明请参考：[SCRIPT_MANUAL.md](SCRIPT_MANUAL.md)

## 🎯 功能说明

### 艾宾浩斯记忆曲线

系统实现了科学的记忆强化算法，根据艾宾浩斯遗忘曲线自动安排复习：

| 阶段 | 时间间隔 | 说明 |
|------|---------|------|
| 阶段 0 | 新题 | 首次学习 |
| 阶段 1 | 30分钟后 | 短期记忆强化 |
| 阶段 2 | 12小时后 | 中期记忆巩固 |
| 阶段 3 | 1天后 | 长期记忆开始形成 |
| 阶段 4 | 2天后 | 记忆稳定性提升 |
| 阶段 5 | 4天后 | 记忆持续强化 |
| 阶段 6 | 7天后 | 一周复习节点 |
| 阶段 7 | 15天后 | 长期记忆确立 |
| 阶段 8 | - | 已掌握，无需复习 |

**规则**：
- 答对：进入下一阶段
- 答错：回到第 1 阶段重新开始

### 刷题模式

- **批次刷题**：每次抽取一组题目（默认 10 题）
- **实时反馈**：批次结束后统一评分，查看详细解析
- **灵活控制**：支持跳过题目，自由安排答题节奏
- **进度追踪**：记录每道题的答题状态和复习阶段

### 考试模式

- **真实模拟**：完全模拟考试环境，答题过程中不显示答案
- **多种模式**：
  - 固定题集考试：按预设题目顺序出题
  - 动态抽取：根据难度、题型等条件随机抽题
- **成绩分析**：考试结束后提供详细成绩报告

### 错题本

- **自动记录**：答错的题目自动加入错题本
- **错题统计**：按课程、题型、难度等多维度分析
- **一键重练**：支持批量重试错题，针对性巩固

### 学习统计 *[WIP]*

> ⚠️ 此模块正在开发中，功能尚不完善。

- **总体概况**：总答题数、正确率、掌握题目数
- **进度追踪**：课程学习进度、待复习题目数
- **趋势分析**：学习时间分布、成绩变化曲线

## 📥 数据导入

系统支持多种格式的题库导入，详细说明请参考 [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md)。

### Markdown 格式

```bash
# 转换 Markdown 为 JSON
cd scripts
uv run python convert_md_to_json.py -f sample_quiz.md

# 导入到数据库
uv run python import_questions.py \
  --json-file sample_quiz.json \
  --course-code llm_basic
```

### Word 文档格式

```bash
# 转换 Word 为 JSON（需用红色标记正确答案）
uv run python convert_docx_to_json.py -i data/input/exam_questions.docx

# 导入为固定题集
uv run python import_questions.py \
  --json-file exam_questions.json \
  --course-code ml_cert_exam \
  --question-set-code exam_set1 \
  --question-set-name "2025年模拟考试题集"
```

## 🔌 API 文档

启动后端服务后，访问以下地址查看完整 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要 API 端点

| 模块 | 端点 | 描述 |
|------|------|------|
| 用户管理 | `/api/users` | 用户创建、查询、统计 |
| 课程管理 | `/api/courses` | 课程列表、详情 |
| 题集管理 | `/api/question-sets` | 题集列表、题目查询 |
| 刷题模式 | `/api/quiz` | 批次刷题、提交答案 |
| 考试模式 | `/api/exam` | 开始考试、提交答案 |
| 复习调度 | `/api/review` | 获取复习题目、提交答案 |
| 错题管理 | `/api/mistakes` | 错题列表、重试错题 |

## 🛠️ 开发指南

### 添加新功能

**后端**：

1. 在 `app/models/` 中创建数据模型
2. 在 `app/services/` 中实现业务逻辑
3. 在 `app/api/` 中创建 API 路由
4. 在 `main.py` 中注册路由

**前端**：

1. 在 `app/` 中创建新页面
2. 在 `components/` 中创建可复用组件
3. 在 `lib/api.ts` 中添加 API 方法
4. 使用 Tailwind CSS 编写样式

### 环境变量

**后端** (`.env`)：

```env
DATABASE_URL=sqlite:///./data/app.db
SECRET_KEY=your-secret-key-change-me
DEV_MODE=true
```

**前端** (`.env.local`)：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📚 详细文档

- [后端开发文档](src/backend/README.md) - 后端架构、API 设计、开发指南
- [前端开发文档](src/frontend/README.md) - 前端架构、组件设计、样式指南
- [脚本使用手册](SCRIPT_MANUAL.md) - 数据导入、格式转换、初始化流程
- [RAG 架构设计](RAG_ARCHITECTURE.md) - 向量检索、知识库管理、版本控制
- [项目亮点](PROJECT_HIGHLIGHTS.md) - 面向求职简历的项目亮点总结

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目基于 GNU Affero General Public License v3.0 (AGPL-3.0) 开源。详见 [LICENSE](LICENSE) 文件。

> **注意**：AGPL 许可证要求如果您在网络上运行此软件的修改版本，必须向用户提供源代码。

## 📊 系统规模

| 模块 | 数量 |
|------|------|
| 后端 API 路由 | 16+ |
| Service 层 | 9+ |
| 数据模型 (SQLAlchemy) | 14+ |
| 前端页面 | 7+ |
| 前端组件 | 10+ |
| RAG 子模块 | 6 |
| Docker 服务 | 6 |

---

**开始学习之旅**：[访问在线演示](http://localhost:3000) 或 [本地部署](#快速开始)

如有问题，请提交 [Issue](https://github.com/yourusername/aie55_llm5_learnhub/issues) 或联系维护者。
