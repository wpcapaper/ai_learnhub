# 课程导入流程指南

本文档介绍如何使用脚本工具导入课程内容并生成题目。

---

## 目录

- [环境配置](#环境配置)
- [脚本概览](#脚本概览)
- [完整流程](#完整流程)
- [脚本详细说明](#脚本详细说明)
- [常见问题](#常见问题)

---

## 环境配置

### 1. 创建 .env 文件

在 `src/backend/` 目录下创建 `.env` 文件：

```bash
cp src/backend/.env.example src/backend/.env
```

### 2. 配置 LLM API

编辑 `.env` 文件，配置以下必要参数：

```env
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
```

#### 支持的 LLM 服务

| 服务商 | LLM_BASE_URL | 说明 |
|--------|--------------|------|
| OpenAI | `https://api.openai.com/v1` | 默认值 |
| DeepSeek | `https://api.deepseek.com` | 国产大模型 |
| 火山引擎 | `https://ark.cn-beijing.volces.com/api/v3` | 字节跳动 |
| 其他 | 自定义 | 需兼容 OpenAI API 格式 |

### 3. 安装依赖

```bash
cd scripts
uv sync
```

---

## 脚本概览

| 脚本 | 用途 | 是否需要 LLM |
|------|------|-------------|
| `init_db.py` | 初始化数据库表结构 | 否 |
| `init_course_data.py` | 初始化默认课程数据 | 否 |
| `import_learning_courses.py` | 导入学习类课程（Markdown） | 否 |
| `generate_course_from_url.py` | 从 URL 抓取内容生成课程 | 是 |
| `generate_questions_from_course.py` | 从课程内容生成题目 | 是 |
| `import_questions.py` | 导入题目到数据库 | 否 |
| `batch_import_questions.py` | 批量导入题目 | 否 |
| `convert_md_to_json.py` | Markdown 转 JSON | 否 |
| `convert_docx_to_json.py` | Word 转 JSON | 否 |

---

## 完整流程

### 方式一：导入现有学习课程（推荐）

适用于：已有 Markdown 格式的课程文档

```bash
# 1. 初始化数据库
cd scripts
uv run python init_db.py

# 2. 初始化课程数据
uv run python init_course_data.py

# 3. 导入学习课程
uv run python import_learning_courses.py

# 4. （可选）从课程生成题目
uv run python generate_questions_from_course.py

# 5. 导入题目到数据库
uv run python import_questions.py -f python_basics_01_questions.json -c python_basics
```

### 方式二：从 URL 生成课程

适用于：从网页内容创建新课程

```bash
# 1. 确保已配置 .env 中的 LLM_API_KEY
# 2. 从 URL 生成课程
uv run python generate_course_from_url.py --url "https://example.com/tutorial" --course-code "new_course"

# 3. 从生成的课程创建题目
uv run python generate_questions_from_course.py --course new_course

# 4. 批量导入题目
uv run python batch_import_questions.py
```

### 方式三：导入现有题库

适用于：已有 JSON 格式的题库

```bash
# 1. 将题库文件放入 scripts/data/output/ 目录

# 2. 单文件导入
uv run python import_questions.py -f sample_quiz.json -c course_code

# 3. 或批量导入
uv run python batch_import_questions.py
```

---

## 脚本详细说明

### init_db.py

初始化数据库表结构。

```bash
uv run python init_db.py
```

**首次使用必须执行！**

---

### init_course_data.py

初始化默认课程数据到数据库。

```bash
uv run python init_course_data.py
```

创建的课程包括：
- Python 基础
- Agent 开发教程
- LangChain 入门
- RAG 系统实战指南

---

### import_learning_courses.py

导入 `courses/` 目录下的 Markdown 格式课程文件。

```bash
uv run python import_learning_courses.py
```

**目录结构要求**：
```
courses/
├── python_basics/
│   ├── 01_变量与数据类型.md
│   ├── 02_流程控制.md
│   └── course.json
├── rag_system_practical_guide/
│   ├── 01_problem_and_overview.md
│   └── course.json
└── ...
```

---

### generate_course_from_url.py

从网页 URL 抓取内容，使用 LLM 生成结构化课程文件。

```bash
uv run python generate_course_from_url.py \
  --url "https://docs.python.org/zh-cn/3/tutorial/" \
  --course-code "python_official" \
  --course-name "Python 官方教程"
```

**参数说明**：
| 参数 | 必填 | 说明 |
|------|------|------|
| `--url` | 是 | 要抓取的网页 URL |
| `--course-code` | 是 | 课程代码（用于标识） |
| `--course-name` | 否 | 课程名称 |
| `--output-dir` | 否 | 输出目录（默认 `courses/`） |

**依赖**：
- `beautifulsoup4`（推荐安装，用于更好的 HTML 解析）

```bash
uv pip install beautifulsoup4
```

---

### generate_questions_from_course.py

读取 Markdown 格式的课程文件，使用 LLM 自动生成选择题。

```bash
uv run python generate_questions_from_course.py --course python_basics
```

**参数说明**：
| 参数 | 必填 | 说明 |
|------|------|------|
| `--course` | 否 | 指定课程目录名（默认处理所有课程） |
| `--output-dir` | 否 | 输出目录（默认 `data/output/`） |

**输出文件命名**：
```
{course_code}_{chapter_name}_questions.json
```

**生成题目格式**：
```json
[
  {
    "content": "题目内容",
    "question_type": "single_choice",
    "options": {
      "A": "选项A",
      "B": "选项B",
      "C": "选项C",
      "D": "选项D"
    },
    "correct_answer": "A",
    "explanation": "答案解析",
    "difficulty": 2,
    "knowledge_points": ["知识点1"]
  }
]
```

---

### import_questions.py

将 JSON 格式的题目导入数据库。

```bash
# 单文件导入
uv run python import_questions.py \
  -f data/output/python_basics_01_questions.json \
  -c python_basics

# 多文件导入（逗号分隔）
uv run python import_questions.py \
  -f "file1.json,file2.json" \
  -c python_basics

# 导入并创建题集
uv run python import_questions.py \
  -f exam_questions.json \
  -c ai_cert_exam \
  -s exam_set_2024 \
  -n "2024年模拟考试"
```

**参数说明**：
| 参数 | 必填 | 说明 |
|------|------|------|
| `-f, --json-file` | 是 | JSON 文件路径（支持多文件逗号分隔） |
| `-c, --course-code` | 是 | 课程代码 |
| `-s, --question-set-code` | 否 | 题集代码 |
| `-n, --question-set-name` | 否 | 题集名称 |
| `-i, --init-db` | 否 | 同时初始化数据库 |

---

### batch_import_questions.py

自动扫描 `data/output/` 目录，批量导入所有题目文件。

```bash
uv run python batch_import_questions.py
```

**文件名格式要求**：
```
{course_code}_{chapter_name}_questions.json
```

**自定义课程列表**：

如果你的课程不在默认列表中，编辑脚本中的 `KNOWN_COURSES` 数组：

```python
KNOWN_COURSES = [
    "agent_development_tutorial",
    "langchain_introduction",
    "rag_system_practical_guide",
    "python_basics",
    # 在这里添加你的课程代码
    "your_new_course_code",
]
```

---

### convert_md_to_json.py

将 Markdown 格式的题库转换为 JSON 格式。

```bash
uv run python convert_md_to_json.py -f data/input/quiz.md
```

---

### convert_docx_to_json.py

将 Word 文档格式的题库转换为 JSON 格式。

```bash
uv run python convert_docx_to_json.py -i data/input/exam.docx
```

**要求**：正确答案需用红色字体标记。

---

## 常见问题

### Q: 提示 `LLM_API_KEY environment variable not set`

A: 检查 `.env` 文件是否正确配置：
1. 文件位置应为 `src/backend/.env`
2. 确保 `LLM_API_KEY` 已填写
3. 确保没有多余的空格或引号

### Q: 题目生成质量不高怎么办？

A: 可以尝试：
1. 使用更强大的模型（如 `gpt-4`）
2. 调整课程内容，确保结构清晰
3. 手动编辑生成的 JSON 文件进行修正

### Q: 如何添加新的课程？

A: 步骤如下：
1. 在 `scripts/init_course_data.py` 中添加课程定义
2. 运行 `uv run python init_course_data.py`
3. 将课程 Markdown 文件放入 `courses/{course_code}/` 目录
4. 在 `batch_import_questions.py` 的 `KNOWN_COURSES` 中添加课程代码

### Q: 数据库在哪里？

A: 默认使用 SQLite，数据库文件位于 `src/backend/data/app.db`。

### Q: 如何重置数据库？

A: 删除数据库文件后重新初始化：
```bash
rm src/backend/data/app.db
cd scripts
uv run python init_db.py
uv run python init_course_data.py
```

---

## 目录结构

```
aie55_llm5_learnhub/
├── src/backend/.env          # 环境变量配置
├── courses/                  # 课程 Markdown 文件
│   ├── python_basics/
│   ├── rag_system_practical_guide/
│   └── ...
├── scripts/
│   ├── data/
│   │   ├── input/           # 输入文件（待转换）
│   │   └── output/          # 输出文件（生成的 JSON）
│   ├── init_db.py
│   ├── init_course_data.py
│   ├── import_learning_courses.py
│   ├── generate_course_from_url.py
│   ├── generate_questions_from_course.py
│   ├── import_questions.py
│   ├── batch_import_questions.py
│   └── ...
└── COURSE_IMPORT_GUIDE.md   # 本文档
```

---

## 相关文档

- [SCRIPT_MANUAL.md](./SCRIPT_MANUAL.md) - 脚本使用手册
- [README.md](./README.md) - 项目说明
