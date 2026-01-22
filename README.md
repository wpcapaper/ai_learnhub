# AILearn Hub

> 基于艾宾浩斯遗忘曲线的 AI 智能学习系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)

## 📖 项目简介

AILearn Hub 是一个现代化的智能学习平台，通过科学的学习算法帮助用户高效掌握知识。系统集成了刷题、考试、复习等多种学习模式，特别适合认证考试备考、技能提升等场景。

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

- **📊 全面的学习统计** *[WIP]*
  - 答题准确率、学习时长、掌握程度等多维度数据
  - 课程进度追踪，可视化展示学习成果
  - 错题统计分析，发现知识盲区
  > ⚠️ 注意：学习统计模块正在开发中，部分功能可能不完善

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

## 🏗️ 技术架构

### 后端技术栈

- **FastAPI**: 现代、高性能的 Web 框架
  - 自动生成 OpenAPI 文档
  - 类型验证（Pydantic）
  - 异步支持
- **SQLAlchemy**: Python ORM
- **数据库**: SQLite（开发环境）/ PostgreSQL（生产环境）
- **Python**: 3.11+

### 前端技术栈

- **Next.js 16**: React 框架（App Router）
  - 服务端渲染（SSR）
  - 自动代码分割
  - 文件系统路由
- **React 19**: UI 库
- **TypeScript**: 类型安全
- **Tailwind CSS 4**: 快速 UI 开发
- **KaTeX**: 数学公式渲染

### 数据导入工具

- **Python**: 脚本开发语言
- **uv**: 快速的 Python 包管理工具
- **python-docx**: Word 文档解析
- **Markdown**: 标准文本格式支持

## 📁 项目结构

```
aie55_llm5_learnhub/
├── src/
│   ├── backend/                 # 后端服务（FastAPI）
│   │   ├── main.py             # 应用入口
│   │   ├── app/
│   │   │   ├── core/           # 核心模块（数据库、艾宾浩斯算法）
│   │   │   ├── models/         # 数据模型
│   │   │   ├── services/       # 业务逻辑
│   │   │   └── api/            # API 路由
│   │   ├── data/               # 数据库文件
│   │   └── Dockerfile
│   │
│   └── frontend/               # 前端应用（Next.js）
│       ├── app/                # 页面目录
│       │   ├── page.tsx        # 首页
│       │   ├── quiz/           # 刷题页面
│       │   ├── exam/           # 考试页面
│       │   ├── mistakes/       # 错题本页面
│       │   ├── stats/          # 统计页面
│       │   └── courses/        # 课程页面
│       ├── components/         # 可复用组件
│       ├── lib/                # 工具库（API Client）
│       └── Dockerfile
│
├── scripts/                    # 数据导入脚本
│   ├── init_db.py             # 初始化数据库
│   ├── init_course_data.py    # 初始化课程数据
│   ├── import_questions.py    # 导入题目
│   ├── convert_md_to_json.py  # Markdown 转 JSON
│   ├── convert_docx_to_json.py # Word 转 JSON
│   └── data/
│       ├── input/              # 输入数据源
│       └── output/             # 转换后的 JSON
│
├── schema.sql                  # 数据库结构定义
├── docker-compose.yml          # Docker Compose 配置
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

# 启动所有服务
docker-compose up -d

# 访问应用
# 前端：http://localhost:3000
# 后端 API：http://localhost:8000
# API 文档：http://localhost:8000/docs
```

### 方式二：本地开发

#### 1. 后端启动

```bash
# 进入后端目录
cd src/backend

# 安装依赖（使用 uv 更快）
pip install -r requirements.txt
# 或使用 uv: uv sync

# 启动开发服务器
uvicorn main:app --host 0.0.0.0 --reload --port 8000
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

## 🙏 致谢

感谢所有为本项目做出贡献的开发者！

---

**开始学习之旅**：[访问在线演示](http://localhost:3000) 或 [本地部署](#快速开始)

如有问题，请提交 [Issue](https://github.com/yourusername/aie55_llm5_learnhub/issues) 或联系维护者。
