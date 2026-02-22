# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

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

## 2026-02-20

### Features
- **UI 重构** - Magic UI 组件库集成，4 种主题切换，Particles/MagicCard/BorderBeam 动效
- **章节详情页增强** - 字数统计、预计阅读时间、左侧大纲导航、返回顶部按钮

### Refactor
- **端口优化** - Admin Frontend 8080，Langfuse 9090，服务端口分离
- **CORS 安全** - 环境变量配置替代通配符
- **Docker 配置** - 统一 frontend 与 admin-frontend 构建配置

---

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

## 2026-02-04

### Features
- **学习课程系统** - Chapter 模型、ReadingProgress 模型、Markdown 阅读器、AI 助手

---

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

## 2026-01-22

### Features
- **刷题模式自动开启批次** - 批次为空时自动创建

### Fixed
- **批次刷题题目推荐** - 艾宾浩斯复习与轮次管理解耦，修复第二轮无法获取题目
- **题目来源标签** - 刷题页面与错题本显示格式统一

---

## 2026-01-21

### Features
- **历史答题记录** - `user_answer_history` 表，追踪所有答题历史

### Fixed
- **课程页统计** - 已刷题目改为当前轮次数量
- **轮次管理** - 新增 `completed_in_current_round` 字段，轮次与复习阶段解耦

---