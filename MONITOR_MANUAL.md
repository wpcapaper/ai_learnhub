# Langfuse 监控使用手册

> 本文档介绍如何在 Langfuse 中查看大模型（LLM）调用记录

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [查看 LLM 调用](#查看-llm-调用)
- [监控功能详解](#监控功能详解)
- [高级使用](#高级使用)
- [常见问题](#常见问题)

---

## 概述

### 什么是 Langfuse？

Langfuse 是一个开源的 LLM 应用可观测性平台，用于追踪、调试和分析大模型调用。本项目已集成 Langfuse，自动记录以下操作：

| 操作类型 | 追踪内容 |
|---------|---------|
| **LLM 调用** | AI 助手对话、问题生成等 |
| **Embedding** | 文本向量化调用 |
| **Rerank** | 搜索结果重排序 |

### 架构说明

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   前端应用       │────▶│   后端 API      │────▶│   LLM 服务      │
│  (Next.js)      │     │   (FastAPI)     │     │  (DeepSeek)     │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Langfuse      │
                        │   (监控平台)     │
                        │  localhost:3001 │
                        └─────────────────┘
```

---

## 快速开始

### 1. 启动服务

```bash
# 在项目根目录执行
docker-compose up -d
```

等待所有服务启动完成（约 30-60 秒）。

### 2. 验证服务状态

```bash
# 检查所有容器是否运行
docker-compose ps

# 期望输出：所有服务状态为 "Up" 或 "healthy"
```

### 3. 首次登录 Langfuse

1. 打开浏览器访问：**http://localhost:3001**

2. 首次访问需要创建账号：
   - 点击 **Sign up** 注册
   - 填写邮箱和密码
   - 完成注册后登录

### 4. 创建项目和获取 API Keys

1. 登录后，点击 **Settings**（设置）→ **Projects**（项目）

2. 点击 **Create Project** 创建新项目
   - 项目名称：如 `AILearn Hub`
   - 点击 **Create** 确认

3. 进入项目后，点击 **API Keys** 标签页

4. 复制以下两个 Key：
   - **Public Key**（以 `pk-` 开头）
   - **Secret Key**（以 `sk-` 开头）

### 5. 配置后端环境变量

编辑 `src/backend/.env` 文件，添加 Langfuse 配置：

```env
# Langfuse 配置
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxx  # 替换为你的 Public Key
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxx  # 替换为你的 Secret Key
LANGFUSE_HOST=http://localhost:3001
```

### 6. 重启后端服务

```bash
docker-compose restart backend
```

### 7. 验证配置生效

1. 在应用中进行一些 AI 相关操作（如与 AI 助手对话）
2. 刷新 Langfuse 页面，查看是否有新的 Trace 记录

---

## 查看 LLM 调用

### 方式一：通过 Traces 列表

1. 登录 Langfuse：http://localhost:3001

2. 在左侧导航栏点击 **Traces**

3. 你将看到所有 LLM 调用的记录列表：

   ```
   | 名称          | 时间         | 耗时    | 标签        |
   |--------------|-------------|---------|------------|
   | ai_chat      | 2分钟前      | 1.2s    | assistant  |
   | embedding    | 5分钟前      | 0.3s    | rag        |
   | rerank       | 10分钟前     | 0.5s    | rag        |
   ```

4. 点击任意一条记录查看详情

### 方式二：通过时间范围过滤

1. 在 Traces 页面顶部，使用时间选择器
2. 选择预设范围（最近 1 小时、24 小时、7 天）或自定义范围
3. 快速定位特定时间段的调用

### 方式三：通过标签过滤

本系统预设了以下标签：

| 标签 | 说明 |
|------|------|
| `assistant` | AI 助手对话 |
| `rag` | RAG 相关操作（Embedding、Rerank）|
| `embedding` | 文本向量化 |
| `rerank` | 结果重排序 |
| `error` | 调用失败 |

在 Traces 页面左侧的 **Filters** 面板中选择标签进行过滤。

---

## 监控功能详解

### Trace（追踪）详情

点击任意 Trace 记录，进入详情页面：

#### 1. 基本信息

```
名称：ai_chat
ID：trace_xxxxx
时间：2026-02-19 10:30:45
耗时：1234ms
```

#### 2. 输入输出

**Input（输入）**：
```json
{
  "args": null,
  "kwargs": {
    "messages": "[{\"role\": \"user\", \"content\": \"什么是机器学习？\"}]",
    "temperature": "0.7"
  }
}
```

**Output（输出）**：
```json
{
  "content": "机器学习是人工智能的一个分支，它使计算机能够..."
}
```

#### 3. Span（子操作）

每个 Trace 包含一个或多个 Span，展示调用细节：

```
├── ai_chat (Trace)
    ├── ai_chat_call (Span)
        ├── 开始时间：10:30:45.000
        ├── 结束时间：10:30:46.234
        ├── 耗时：1234ms
        └── 元数据：{"model": "deepseek-chat"}
```

### Metrics（指标）

在 Langfuse 顶部导航点击 **Dashboard**，可以看到：

- **Total Traces**：总追踪数
- **Total Observations**：总观察数（Span 数量）
- **Average Latency**：平均延迟
- **Error Rate**：错误率

### 成本估算

Langfuse 会根据 Token 使用量估算成本：

1. 进入 **Dashboard** 页面
2. 查看 **Model Usage** 部分
3. 按 Token 数量和模型定价计算费用

> **注意**：成本估算基于 Langfuse 内置的模型定价表，可能与实际账单有差异。

---

## 高级使用

### 按 Session 追踪

如果你的应用支持用户会话，可以按 Session ID 查看同一用户的所有调用：

1. 在代码中设置 Session ID：
   ```python
   from app.llm.langfuse_wrapper import _get_langfuse_client
   
   client = _get_langfuse_client()
   client.trace(
       name="ai_chat",
       session_id="user_123_session",  # 用户会话 ID
       ...
   )
   ```

2. 在 Langfuse 中按 Session ID 过滤

### 导出数据

1. 在 Traces 页面，点击右上角的 **Export** 按钮
2. 选择导出格式（CSV、JSON）
3. 下载文件进行离线分析

### 配置告警（企业版）

如果你使用 Langfuse Cloud 或企业版，可以配置：
- 错误率告警
- 延迟告警
- Token 使用量告警

---

## 常见问题

### Q1: Langfuse 页面打开很慢？

**原因**：Langfuse v2 首次启动需要初始化数据库。

**解决**：等待 1-2 分钟后刷新页面。

### Q2: 没有看到任何 Trace 记录？

**检查清单**：
1. 确认 Langfuse 服务正常运行：
   ```bash
   docker-compose ps langfuse
   # 状态应为 "healthy"
   ```

2. 确认后端环境变量已正确配置：
   ```bash
   docker-compose exec backend env | grep LANGFUSE
   # 应显示 LANGFUSE_PUBLIC_KEY 和 LANGFUSE_SECRET_KEY
   ```

3. 确认后端服务已重启：
   ```bash
   docker-compose restart backend
   ```

4. 在应用中触发一次 LLM 调用（如与 AI 助手对话）

### Q3: 如何关闭 Langfuse 监控？

在 `src/backend/.env` 中添加：
```env
LANGFUSE_ENABLED=false
```

然后重启后端：
```bash
docker-compose restart backend
```

### Q4: Langfuse 数据存在哪里？

数据存储在 Docker Volume `langfuse_db_data` 中：
- 位置：PostgreSQL 数据库（langfuse-db 容器）
- 持久化：即使容器重启，数据也不会丢失

### Q5: 如何清空 Langfuse 数据？

```bash
# 停止所有服务
docker-compose down

# 删除 Langfuse 数据卷
docker volume rm aie55_llm5_learnhub_langfuse_db_data

# 重新启动（数据将重新初始化）
docker-compose up -d
```

> **警告**：此操作会删除所有历史监控数据，无法恢复！

### Q6: 生产环境如何部署？

**推荐使用 Langfuse Cloud（SaaS）**：

1. 访问 https://cloud.langfuse.com 注册账号
2. 创建项目并获取 API Keys
3. 修改环境变量：
   ```env
   LANGFUSE_HOST=https://cloud.langfuse.com
   LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
   LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
   ```
4. 移除 docker-compose.yml 中的 langfuse 和 langfuse-db 服务

**自托管生产部署**：

参考官方文档部署 Langfuse v3（需要 ClickHouse、MinIO 等额外组件）。

---

## 参考链接

- [Langfuse 官方文档](https://langfuse.com/docs)
- [Langfuse GitHub](https://github.com/langfuse/langfuse)
- [项目 LLM 架构文档](./change_log/llm_architecture_refactor_20260219.md)

---

**更新日期**：2026-02-19
