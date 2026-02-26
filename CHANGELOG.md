# Changelog

All notable changes to this project will be documented in this file.

---

## [MISTAKES-001] - 2026-02-26

### Fixed
- MISTAKES-001: 修复错题本用户答案显示"未作答"的问题（字段名 answer → user_answer）



## [KB-ADMIN-002] - 2026-02-24

### Changed
- 知识库管理页改为统一使用课程代码 + 章节文件的 RAG 管理接口
- 管理端 API 客户端修正文档块详情查询参数为 code
- 知识库管理页课程列表接口改为 markdown-courses
- 章节配置/检索/索引接口改用 chapter_order 参数
- 课程批量索引接口改为服务端从 course.json 读取章节
- 知识库管理路由改为独立加载

## [KB-ADMIN-003] - 2026-02-25

### Changed
- KB-ADMIN-003: 章节序号解析增加类型归一与课程路径回退
- KB-ADMIN-003: 修复容器路径回退越界导致的 500
- KB-ADMIN-003: 修正项目根目录解析以匹配容器路径
- KB-ADMIN-004: 章节分块计数与列表刷新对齐

## [RAG-CE-001] - 2026-02-25

### Changed
- RAG-CE-001: ai_chat 支持可选 RAG 召回并提供 C 端 RAG 查询接口

## [RAG-CE-002] - 2026-02-25

### Changed
- RAG-CE-002: 移除 ai_chat RAG 参数与 C 端 RAG 查询接口，提供 RAG 工具函数

## [RAG-CE-003] - 2026-02-25

### Changed
- RAG-CE-003: RAG 工具支持章节维度召回并新增接入说明
- RAG-CE-003: 忽略 .bak 备份文件

## [TEST-ARCH-001] - 2026-02-25

### Changed
- TEST-ARCH-001: 对齐索引任务单元测试与当前任务函数签名
- TEST-ARCH-001: 添加后端单元测试运行与覆盖链路文档

## [AI-CHAT-001] - 2026-02-25

### Changed
- AI-CHAT-001: ai_chat 使用章节优先召回提示词并保留旧版
- 清理无用的 .bak 备份文件

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## [RAG-ARCH-001] - 2026-02-24

### Changed
 知识库管理模块重构：按照 RAG_ARCHITECTURE.md 规范重构
 Collection命名：`course_{source}_{code}` → `course_{code}_{kb_version}`
 Metadata字段：精简为 code, source_file, position, char_start, char_end, content_type, char_count, estimated_tokens, kb_version
 Chunk ID：随机UUID → `{code}__{file_hash}__{position:04d}` 稳定位置ID
 版本管理：通过 course.json 的 kb_version 字段集中管理

### Files
 `src/backend/app/rag/chunking/metadata.py`
 `src/backend/app/rag/chunking/strategies.py`
 `src/backend/app/rag/vector_store/chroma.py`
 `src/backend/app/rag/service.py`
 `src/backend/app/api/admin_kb.py`
 `src/backend/app/tasks/jobs.py`
 `src/admin-frontend/app/knowledge-base/page.tsx`

## [admin-fix-0224] - 2026-02-24

### Fixed
 Admin API 变量未定义：批量重命名 `course_id` → `course_code` 时漏改函数参数
 Markdown 转换切碎：`_split_by_h1` 方法将代码块内的注释误判为 H1 标题

### Changed
 `admin.py`：补全 8 处 URL 参数和 Request 模型字段 `course_id` → `course_code`
 `converters/__init__.py`：`_split_by_h1` 方法添加代码块检测逻辑
 `optimization/page.tsx`：前端请求体 `course_id` → `course_code`

### Files
 `src/backend/app/api/admin.py`
 `src/backend/app/course_pipeline/converters/__init__.py`
 `src/admin-frontend/app/optimization/page.tsx`

### Fixed
- Admin API 变量未定义：`admin.py` 中 6 个函数使用未定义的 `course_code` 变量
- Markdown 转换切碎：`_split_by_h1` 方法将代码块内的注释误判为 H1 标题

### Changed
- `admin.py`：修复 6 处 `course_code` -> `course_id` 变量名问题
- `converters/__init__.py`：`_split_by_h1` 方法添加代码块检测逻辑

### Files
- `src/backend/app/api/admin.py`
- `src/backend/app/course_pipeline/converters/__init__.py`

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## [wc-fix-0224] - 2026-02-24

### Fixed
 单课程转换 API 章节排序乱序：`admin.py` 手动构建 source_files 时遗漏排序
 词云组件崩溃：前端访问 API 返回数据时缺少防御性编程

### Changed
 `admin.py`：添加 `source_files.sort(key=lambda f: f.path)`
 `jobs.py`：重写 `generate_wordcloud` 函数支持异步词云生成
 `WordcloudViewer.tsx`：添加 `?.` 安全访问

### Files
 `src/backend/app/api/admin.py`
 `src/backend/app/tasks/jobs.py`
 `src/frontend/components/WordcloudViewer.tsx`

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## [course_import_lifecycle_refactor_20260223] - 2026-02-23

### Changed
 课程转换管道：首次转换不再添加版本号后缀，不自动排序
 课程导入：使用 UUID 作为数据库主键，用 code 查重
 单一数据源：移除冗余的 courses/ 目录

### Removed
 批量导入 API：`POST /api/admin/courses/import`
 批量转换 API：`POST /api/admin/courses/convert`（保留单课程转换）

### Added
 章节重排 API：`POST /api/admin/courses/reorder/{code}` (TODO)
 生命周期文档：`FILE_LIFE_CIRCLE.md`

### Files
 `src/backend/app/course_pipeline/pipeline.py`
 `src/backend/app/api/admin.py`
 `src/backend/tests/test_course_refactor.py`
 `FILE_LIFE_CIRCLE.md`

## [Unreleased]
### Changed
- 词云 API 重构：管理端使用 `course_code` 作为路径参数
- 章节词云 API：从 `chapter_name` 改为 `chapter_order`（章节序号）
- 课程转换排序：`source_files` 按文件名字典序排列
- Pydantic 模型：移除 `WordcloudStatusResponse` 等无用的必填字段

### Added
- C端章节词云：学习页面新增词云按钮和弹窗组件
- `validate_chapter_name()` 函数：支持中文字符的章节名称验证
- C端 API：新增 `by-id` 和 `by-code` 两套词云查询接口

### Fixed
- 管理端词云按钮：`course.id` → `course.code`
- 章节词云查询：解决中文文件名 URL 编码导致的 400 错误

### Files
- `src/backend/app/api/admin.py`
- `src/backend/app/api/courses.py`
- `src/backend/app/services/wordcloud_service.py`
- `src/backend/app/core/admin_security.py`
- `src/backend/app/course_pipeline/pipeline.py`
- `src/admin-frontend/lib/api.ts`
- `src/admin-frontend/app/page.tsx`
- `src/admin-frontend/components/WordcloudManager.tsx`
- `src/frontend/lib/api.ts`
- `src/frontend/app/learning/page.tsx`
- `src/frontend/components/WordcloudViewer.tsx`
- `src/frontend/components/ChapterWordcloudModal.tsx` (新增)

### Added
- 章节详情页：字数统计、预计用时、左侧大纲导航、返回顶部按钮
- Admin Frontend：独立的 Next.js 15 管理前端，基于 Skills 的 Agent 框架
- RAG 系统：向量检索、Embedding、Rerank 能力，为 AI 助教提供课程内容智能检索
- 课程转换管道：支持 Markdown 和 Jupyter Notebook 格式转换
- 历史答题记录功能：追踪用户历史上做错过的题目
- 错题重练功能：错题本页面一键重练全部错题
- 4 种主题配色：现代科技风、清新自然、暖阳橙、学者蓝

### Changed
- Admin API：增加 IP 白名单认证保护
- 端口规划：Admin Frontend → 8080，Langfuse → 9090
- CORS：从 `allow_origins=["*"]` 改为环境变量配置
- LLM 架构：统一 LLM 调用接口，集成 Langfuse 监控
- 艾宾浩斯算法：首次答对直接视为已掌握（stage 8）
- 批次刷题：自动开启新批次、轮次管理与艾宾浩斯算法解耦

### Fixed
- Langfuse 监控：trace 的 Input/Output 为空问题
- 课程页已刷题目统计：改为当前轮次已刷数量
- 轮次管理：固定题集考试后无法开启新轮次
- 批次刷题题目推荐：第二轮开始时无法获取题目
- 刷题页面滚动：内容可被滚出屏幕问题
- 深色主题：部分文字颜色不可见问题

### Removed
- 学习统计模块：无业务价值
- 冗余的子目录 `.env.example`：统一到根目录

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## 2026-02-20

### Features
- **UI 重构** - Magic UI 组件库集成，4 种主题切换，Particles/MagicCard/BorderBeam 动效
- **章节详情页增强** - 字数统计、预计阅读时间、左侧大纲导航、返回顶部按钮

### Refactor
- **端口优化** - Admin Frontend 8080，Langfuse 9090，服务端口分离
- **CORS 安全** - 环境变量配置替代通配符
- **Docker 配置** - 统一 frontend 与 admin-frontend 构建配置

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## 2026-02-19

### Features
- **Admin Frontend Agent 化** - Skills-based Agent 框架，SSE 流式输出
- **RAG 系统集成** - 向量检索、Embedding、Rerank、课程质量评估
- **课程转换管道** - Markdown/Jupyter Notebook 格式支持，章节自动排序

### Refactor
- **LLM 架构重构** - 统一封装层，Langfuse 监控覆盖 LLM/Embedding/Rerank
- **Redis Queue** - 异步任务框架，为任务型 Agent 做准备

### Fixed
- **Langfuse 监控** - trace 数据 Input/Output 为空、Latency/Usage 为 0

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## 2026-02-04

### Features
- **学习课程系统** - Chapter 模型、ReadingProgress 模型、Markdown 阅读器、AI 助手

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## 2026-01-23

### Features
- **批次完成页** - 新增"开启新的批次"按钮
- **轮次检查** - 刷题模式自动检查是否可开启新轮次
- **错题重练** - 错题本一键重练全部错题 (`POST /api/mistakes/retry-all`)

### Changed
- **艾宾浩斯算法** - 首次答对直接视为已掌握（stage 8）
- **考试模式** - 题目来源标签同步显示

### Fixed
- **深色主题** - AI 助手默认图标不可见问题

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## 2026-01-22

### Features
- **刷题模式自动开启批次** - 批次为空时自动创建

### Fixed
- **批次刷题题目推荐** - 艾宾浩斯复习与轮次管理解耦，修复第二轮无法获取题目
- **题目来源标签** - 刷题页面与错题本显示格式统一

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`


## 2026-01-21

### Features
- **历史答题记录** - `user_answer_history` 表，追踪所有答题历史

### Fixed
- **课程页统计** - 已刷题目改为当前轮次数量
- **轮次管理** - 新增 `completed_in_current_round` 字段，轮次与复习阶段解耦

---

## [KB-ADMIN-001] - 2026-02-24

### Analysis
- RAG 管理模块现状分析：后端已符合 RAG_ARCHITECTURE.md 规范
- 版本 fallback 机制确认：course.json 无 kb_version 时默认为 1
- 管理端前端待简化：移除双数据源概念

### Docs
- `vibe-coding-logs/change_intent/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`
- `vibe-coding-logs/change_log/aie55_llm5_learnhub/KB-ADMIN-001_rag_admin_simplify.md`

## [outline_nav_enhance_0222] - 2026-02-22

### Fixed
- 目录栏点击最后章节跳转错误的问题
- 目录栏当前章节高亮不明显的问题

### Changed
- OutlineNav 从 DOM 读取 headings，避免与 MarkdownReader ID 不一致
- 目录栏当前章节增加加粗和加粗边框效果
- MarkdownReader 底部添加 60vh 占位，确保最后章节可滚动到视口顶部
- 目录栏点击支持 URL hash 更新
- 目录栏性能优化：RAF 节流、缓存 DOM 查询、useCallback
- 目录栏当前章节自动滚动到可见区域

### Files
- `src/frontend/components/OutlineNav.tsx`
- `src/frontend/components/MarkdownReader.tsx`


## [mermaid_chinese_fix_0222] - 2026-02-22

### Fixed
- Mermaid 流程图节点中文字符截断问题（使用等宽字体 + 减小字号）
- OutlineNav 目录栏点击无法跳转问题（改用文本匹配）

### Changed
- Mermaid 使用等宽字体 (ui-monospace) 提高文本宽度测量准确性
- Mermaid 字号减小到 14px 增加容错空间
- OutlineNav handleItemClick 改为通过文本内容和标题级别匹配

### Files
- `src/frontend/components/MarkdownReader.tsx`
- `src/frontend/components/OutlineNav.tsx`
- `src/frontend/app/globals.css`


## [mermaid_progress_fix_20260222] - 2026-02-22

### Fixed
- Mermaid 流程图节点文字被截断的问题
- Progress 接口传递浮点数导致 HTTP 422 错误

### Changed
- 增加 Mermaid 节点内边距配置 (padding: 15)
- Progress 接口的 position 和 percentage 使用 Math.round() 取整

### Files
- `src/frontend/components/MarkdownReader.tsx`
- `src/frontend/app/learning/page.tsx`

## [code_block_theme_fix_20260222] - 2026-02-22

### Fixed
- 代码块语法高亮符号类出现不当背景色的问题
- 代码块不适配前端主题配色（浅色主题下使用深色背景）
- 代码块黑色外边框问题

### Changed
- 浅色主题代码块背景改为浅灰色 (#f6f8fa)
- 新增语法高亮 token 颜色 CSS 变量（浅色/深色各 12 个）
- 移除代码块边框，使用圆角设计
- MarkdownReader 组件使用自定义语法高亮样式

### Files
- `src/frontend/app/globals.css`
- `src/frontend/components/MarkdownReader.tsx`

## [QUIZ-GEN-001] - 2026-02-25

### Changed
- QUIZ-GEN-001: 集成题目生成脚本到管理端 API
- 新增 QuestionGenerationService 服务层
- 新增 POST /api/admin/quiz/generate 端点（同步生成）
- 新增 POST /api/admin/quiz/generate/async 端点（后台任务）
- 新增 GET /api/admin/quiz/generate/{job_id} 端点（状态查询）

### Files
- `src/backend/app/services/question_generation_service.py` (新增)
- `src/backend/app/api/admin.py` (修改)
