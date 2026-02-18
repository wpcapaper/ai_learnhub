# 提示词管理指南

本文档介绍 AILearn Hub 的提示词管理系统，包括提示词的创建、维护和使用方法。

---

## 目录

- [概述](#概述)
- [目录结构](#目录结构)
- [提示词文件格式](#提示词文件格式)
- [PromptLoader API](#promptloader-api)
- [使用示例](#使用示例)
- [最佳实践](#最佳实践)
- [现有提示词](#现有提示词)

---

## 概述

AILearn Hub 使用 YAML + Jinja2 模板的提示词管理方案，具有以下特点：

| 特性 | 说明 |
|------|------|
| **外部化管理** | 提示词与代码分离，独立维护 |
| **模板变量** | 支持 Jinja2 模板语法，灵活替换变量 |
| **缓存机制** | 提高加载性能，支持热重载 |
| **版本追踪** | 提示词变更可独立追踪 |

---

## 目录结构

```
src/backend/prompts/
├── __init__.py              # 模块入口
├── loader.py                # PromptLoader 实现
└── templates/
    ├── ai_assistant.yaml    # AI 课程助教提示词
    └── ...                  # 其他提示词
```

---

## 提示词文件格式

每个提示词使用独立的 YAML 文件，基本结构如下：

```yaml
# 元信息
name: prompt_name
version: "1.0.0"
description: 提示词描述

# 系统提示词（必需）
system_prompt: |
  你是一个 {{ role }}，负责 {{ task }}。
  
  【行为准则】
  1. 准则一
  2. 准则二

# 额外模板（可选）
templates:
  context_template: |
    【上下文信息】
    {{ context_data }}

# 默认变量（可选）
variables:
  role: "助手"
  task: "回答问题"
  max_items: 5

# 元数据（可选）
metadata:
  author: team
  created_at: "2026-02-18"
  updated_at: "2026-02-18"
  tags:
    - tag1
    - tag2
  changelog:
    - version: "1.0.0"
      date: "2026-02-18"
      changes: "初始版本"
```

### 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 否 | 提示词名称，用于标识 |
| `version` | 否 | 版本号，用于追踪变更 |
| `description` | 否 | 提示词描述 |
| `system_prompt` | **是** | 系统提示词内容，支持 Jinja2 模板 |
| `templates` | 否 | 额外的模板定义 |
| `variables` | 否 | 默认变量值 |
| `metadata` | 否 | 元数据信息 |

### Jinja2 模板语法

在提示词中使用 `{{ variable_name }}` 插入变量：

```yaml
system_prompt: |
  你是一个 {{ role }}。
  请生成 {{ count }} 个{{ item_type }}。
```

支持的语法：
- `{{ variable }}` - 变量插值
- `{% if condition %}...{% endif %}` - 条件判断
- `{% for item in list %}...{% endfor %}` - 循环

---

## PromptLoader API

### 基本用法

```python
from prompts import prompt_loader

# 获取完整消息列表
messages = prompt_loader.get_messages(
    "ai_assistant",
    include_templates=["course_context"],
    course_content="课程内容..."
)

# 仅渲染系统提示词
system_prompt = prompt_loader.render("ai_assistant", count=5)

# 获取配置值
max_history = prompt_loader.get_config("ai_assistant", "variables", {}).get("max_history", 10)

# 列出所有可用提示词
prompt_names = prompt_loader.list_prompts()
```

### API 参考

#### `load(name: str) -> Dict`

加载提示词配置。

```python
config = prompt_loader.load("ai_assistant")
print(config['system_prompt'])
```

#### `render(name: str, template_key: str = "system_prompt", **variables) -> str`

渲染指定的模板。

```python
# 渲染系统提示词
content = prompt_loader.render("ai_assistant", suggestion_count=5)

# 渲染额外模板
context = prompt_loader.render("ai_assistant", "course_context", course_content="...")
```

#### `get_messages(name: str, include_templates: List[str] = None, **variables) -> List[Dict]`

获取 OpenAI 格式的消息列表。

```python
messages = prompt_loader.get_messages(
    "ai_assistant",
    include_templates=["course_context"],
    course_content="课程内容...",
    suggestion_count=3
)
# 返回: [{"role": "system", "content": "..."}, {"role": "system", "content": "..."}]
```

#### `get_config(name: str, key: str, default: Any = None) -> Any`

获取配置中的特定值。

```python
max_history = prompt_loader.get_config("ai_assistant", "variables", {}).get("max_history")
```

#### `clear_cache(name: str = None)`

清除缓存。

```python
# 清除指定提示词缓存
prompt_loader.clear_cache("ai_assistant")

# 清除所有缓存
prompt_loader.clear_cache()
```

#### `list_prompts() -> List[str]`

列出所有可用的提示词。

```python
names = prompt_loader.list_prompts()
# 返回: ["ai_assistant", "question_generator", ...]
```

---

## 使用示例

### 在 API 中使用

```python
# app/api/learning.py
from prompts import prompt_loader

async def ai_chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 获取课程内容
    course_content = get_course_content(request.chapter_id)
    
    # 使用提示词加载器构建消息列表
    messages = prompt_loader.get_messages(
        "ai_assistant",
        include_templates=["course_context"],
        course_content=course_content
    )
    
    # 添加历史记录
    for msg in history_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # 调用 LLM
    response = await client.chat.completions.create(
        model=model,
        messages=messages
    )
    # ...
```

### 创建新提示词

1. 在 `prompts/templates/` 目录下创建 YAML 文件：

```yaml
# prompts/templates/summarizer.yaml
name: summarizer
version: "1.0.0"
description: 文本摘要生成器

system_prompt: |
  你是一个专业的文本摘要助手。
  请将以下文本总结为 {{ summary_length }} 字以内的摘要。
  
  要求：
  1. 保留关键信息
  2. 语言简洁
  3. 逻辑清晰

variables:
  summary_length: 200

metadata:
  author: team
  created_at: "2026-02-18"
```

2. 在代码中使用：

```python
from prompts import prompt_loader

messages = prompt_loader.get_messages("summarizer", summary_length=100)
# 添加用户消息
messages.append({"role": "user", "content": long_text})
```

---

## 最佳实践

### 1. 提示词版本管理

每次修改提示词时更新版本号和 changelog：

```yaml
version: "1.1.0"
changelog:
  - version: "1.1.0"
    date: "2026-02-20"
    changes: "优化回答格式，增加代码块支持"
  - version: "1.0.0"
    date: "2026-02-18"
    changes: "初始版本"
```

### 2. 变量命名规范

使用清晰、有意义的变量名：

```yaml
# ✅ 好的命名
variables:
  suggestion_count: 3
  max_history_turns: 10
  response_language: "中文"

# ❌ 避免的命名
variables:
  n: 3
  m: 10
  lang: "中文"
```

### 3. 模块化设计

将复杂提示词拆分为多个模板：

```yaml
system_prompt: |
  {{ role_definition }}
  {{ behavior_guidelines }}
  {{ output_format }}

templates:
  role_definition: |
    你是一个专业的 AI 助教...
  
  behavior_guidelines: |
    【行为准则】
    1. 专业...
    2. 耐心...
  
  output_format: |
    【输出格式】
    回答后生成 {{ suggestion_count }} 个推荐问题...
```

### 4. 测试提示词

修改提示词后进行测试：

```python
# 测试脚本
from prompts import prompt_loader

# 测试加载
config = prompt_loader.load("ai_assistant")
print(f"Name: {config['name']}")
print(f"Version: {config['version']}")

# 测试渲染
messages = prompt_loader.get_messages("ai_assistant", course_content="测试内容")
for msg in messages:
    print(f"Role: {msg['role']}")
    print(f"Content preview: {msg['content'][:100]}...")
```

### 5. 热重载

开发环境可启用自动重载：

```python
# 开发环境
prompt_loader = PromptLoader(enable_cache=True, auto_reload=True)

# 生产环境
prompt_loader = PromptLoader(enable_cache=True, auto_reload=False)
```

---

## 现有提示词

| 名称 | 文件 | 用途 |
|------|------|------|
| `ai_assistant` | `ai_assistant.yaml` | AI 课程助教对话 |

### ai_assistant

AI 课程助教系统提示词，用于解答用户关于课程内容的问题。

**变量**：
| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `suggestion_count` | 3 | 推荐问题数量 |
| `max_history` | 10 | 最大历史记录数 |

**模板**：
| 模板名 | 说明 |
|--------|------|
| `course_context` | 课程内容片段 |

**使用示例**：
```python
messages = prompt_loader.get_messages(
    "ai_assistant",
    include_templates=["course_context"],
    course_content=chapter_content
)
```

---

## 相关文档

- [COURSE_IMPORT_GUIDE.md](./COURSE_IMPORT_GUIDE.md) - 课程导入指南
- [README.md](./README.md) - 项目说明
