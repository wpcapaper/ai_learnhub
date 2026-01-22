# 题目导入 JSON 格式规范

> **重要**：本文档定义了 AILearn Hub 系统题目数据的标准 JSON 格式。
> 所有导入脚本（`import_questions.py`）和数据转换工具（`convert_md_to_json.py`、`convert_docx_to_json.py`）都严格遵循此格式规范。
>
> 自行扩展题库时，请确保 JSON 文件符合本文档定义的格式要求。

---

## 📋 目录

- [格式规范概述](#格式规范概述)
- [标准 JSON 格式](#标准-json-格式)
- [字段详细说明](#字段详细说明)
- [题目类型详解](#题目类型详解)
- [完整示例](#完整示例)
- [格式验证规则](#格式验证规则)
- [扩展指南](#扩展指南)
- [常见问题](#常见问题)
- [格式转换工具](#格式转换工具)

---

## 格式规范概述

### 核心原则

1. **标准优先**：所有导入数据必须遵循标准 JSON 格式
2. **向后兼容**：格式设计支持未来的扩展和增强
3. **可验证性**：提供完整的验证规则和错误提示
4. **易于扩展**：支持通过 `metadata` 字段添加自定义数据

### 支持的数据来源

| 数据来源 | 转换工具 | 输出格式 | 说明 |
|---------|----------|---------|------|
| Markdown 文件 | `convert_md_to_json.py` | 标准 JSON | 支持 `_[单选]_`、`_[多选]_`、`_[判断]_` 格式 |
| Word 文档 | `convert_docx_to_json.py` | 标准 JSON | 支持红色标记正确答案 |
| 手动编辑 | 直接编写 | 标准 JSON | 严格按照本文档格式编写 |
| 第三方工具 | 自定义 | 标准 JSON | 确保输出符合本规范 |

---

## 标准 JSON 格式

### 顶层结构

支持两种格式：

**格式 1：单个题目对象**

```json
{
  "question_type": "single_choice",
  "content": "题目内容",
  "correct_answer": "A",
  "options": {
    "A": "选项A",
    "B": "选项B"
  }
}
```

**格式 2：题目数组（推荐用于批量导入）**

```json
[
  {
    "question_type": "single_choice",
    "content": "题目1",
    "correct_answer": "A",
    "options": { "A": "选项A", "B": "选项B" }
  },
  {
    "question_type": "multiple_choice",
    "content": "题目2",
    "correct_answer": "A,C",
    "options": { "A": "选项A", "B": "选项B", "C": "选项C" }
  }
]
```

### 文件编码

- **编码格式**：UTF-8
- **文件扩展名**：`.json`
- **缩进**：2 或 4 个空格（推荐）
- **行尾符**：LF（Unix 风格）

---

## 字段详细说明

### 必填字段

| 字段名 | 类型 | 说明 | 示例 | 验证规则 |
|--------|------|------|------|---------|
| `question_type` | string | 题目类型 | `"single_choice"` | 见[支持的题目类型](#支持的题目类型) |
| `content` | string | 题目内容 | `"以下哪项是Python的特点？"` | 非空字符串 |
| `correct_answer` | string 或 array | 正确答案 | `"A"` 或 `"A,C"` 或 `["A", "C"]` | 必须符合题目类型的答案格式 |

### 可选字段

| 字段名 | 类型 | 说明 | 默认值 | 示例 |
|--------|------|------|--------|------|
| `id` | string | 题目唯一标识符 | 自动生成 UUID | `"550e8400-e29b-41d4-a716-446655440000"` |
| `options` | object | 选项（选择题必填） | `null` | `{"A": "选项A", "B": "选项B"}` |
| `explanation` | string | 解析/答案说明 | `null` | `"Python是一种解释型语言..."` |
| `knowledge_points` | array | 知识点标签 | `[]` | `["Python基础", "编程语言"]` |
| `difficulty` | integer | 难度等级 (1-5) | `2` | `1` (简单), `5` (困难) |
| `is_controversial` | boolean | 是否有争议 | `false` | `true` 或 `false` |
| `metadata` | object | 额外元数据 | `{}` | `{"source": "官方题库", "author": "张三"}` |

### 支持的题目类型

| 类型值 | 说明 | 是否需要 options | 答案格式 |
|--------|------|----------------|---------|
| `single_choice` | 单选题 | 是 | 单个选项键，如 `"A"` |
| `multiple_choice` | 多选题 | 是 | 逗号分隔的选项键，如 `"A,C"` |
| `true_false` | 判断题 | 是 | `"A"`（对）或 `"B"`（错） |
| `fill_blank` | 填空题 | 否 | 任意字符串 |
| `essay` | 问答题 | 否 | 任意字符串 |

### 字段约束详解

#### `question_type`（题目类型）

**枚举值**：

```json
["single_choice", "multiple_choice", "true_false", "fill_blank", "essay"]
```

**类型说明**：

- `single_choice`：从多个选项中选择一个正确答案
- `multiple_choice`：从多个选项中选择一个或多个正确答案
- `true_false`：判断题，答案为"对"或"错"
- `fill_blank`：填空题，用户输入文本答案
- `essay`：问答题，用户输入长文本答案

#### `content`（题目内容）

**格式要求**：

- 类型：字符串
- 长度：1-2000 个字符
- 编码：UTF-8
- 支持：纯文本、HTML 标签（由前端渲染）

**最佳实践**：

- 保持简洁清晰，避免歧义
- 如果包含数学公式，使用 LaTeX 格式：`$E=mc^2$` 或 `$$\int...$$`
- 避免使用特殊符号（如 `\n`, `\t`），使用换行符制表符

**示例**：

```json
{
  "content": "以下哪项是Python的特点？",
  "explanation": "Python具有解释型、动态类型、语法简洁等特点。"
}
```

```json
{
  "content": "根据相对论，能量和质量的换算公式是？",
  "explanation": "根据爱因斯坦的质能方程，$E=mc^2$。"
}
```

#### `options`（选项）

**格式要求**：

- 类型：对象（键值对）
- 键名：字符串，建议使用字母（A、B、C、D）
- 值：字符串，选项内容
- **必填**：`single_choice`、`multiple_choice`、`true_false`

**标准格式**：

```json
{
  "options": {
    "A": "选项A内容",
    "B": "选项B内容",
    "C": "选项C内容",
    "D": "选项D内容"
  }
}
```

**判断题固定格式**：

```json
{
  "question_type": "true_false",
  "options": {
    "A": "对",
    "B": "错"
  },
  "correct_answer": "A"
}
```

**自定义键名（不推荐）**：

```json
{
  "options": {
    "option1": "选项1",
    "option2": "选项2"
  }
}
```

#### `correct_answer`（正确答案）

**格式规则**：

| 题目类型 | 格式 | 示例 |
|---------|------|------|
| `single_choice` | 单个选项键（字符串） | `"A"` |
| `multiple_choice` | 逗号分隔的选项键（字符串）或数组 | `"A,C"` 或 `["A", "C"]` |
| `true_false` | 选项键（字符串） | `"A"`（对）或 `"B"`（错） |
| `fill_blank` | 任意字符串 | `"def"` |
| `essay` | 任意字符串 | `"列表是可变的，元组是不可变的。"` |

**多选题答案格式**：

支持三种格式：

```json
// 格式 1：逗号分隔的字符串（推荐）
"correct_answer": "A,C,D"

// 格式 2：数组
"correct_answer": ["A", "C", "D"]

// 格式 3：带空格的逗号分隔（会自动清理）
"correct_answer": "A, C, D"
```

**注意**：
- 多选题答案会自动按字母排序，避免顺序问题
- 选项键必须存在于 `options` 对象中
- 大小写敏感，必须使用大写字母（A、B、C、D）

#### `difficulty`（难度等级）

**等级说明**：

| 等级 | 数值 | 说明 | 建议场景 |
|------|------|------|---------|
| 简单 | 1 | 基础概念，容易理解 | 入门学习 |
| 较简单 | 2 | 基础应用，需要一定理解 | 巩固基础 |
| 中等 | 3 | 综合应用，需要多知识点 | 综合练习 |
| 较难 | 4 | 深度理解，需要综合分析 | 深化学习 |
| 困难 | 5 | 复杂问题，需要深度思考 | 挑战练习 |

**默认值**：`2`

**设置示例**：

```json
{
  "difficulty": 1  // 简单
}
```

#### `knowledge_points`（知识点标签）

**格式要求**：

- 类型：字符串数组
- 每个元素：1-50 个字符的字符串
- 用途：题目标签、筛选、统计分析

**示例**：

```json
{
  "knowledge_points": ["Python基础", "数据结构", "算法"]
}
```

```json
{
  "knowledge_points": ["AI基础", "机器学习", "监督学习", "分类算法"]
}
```

**使用场景**：

- 按知识点筛选题目进行专项练习
- 统计用户在各知识点上的掌握情况
- 推荐相似知识点的题目进行复习

#### `metadata`（额外元数据）

**格式要求**：

- 类型：对象（键值对）
- 键名：字符串（自定义）
- 值：任意 JSON 兼容类型

**推荐字段**：

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `source` | string | 数据来源 | `"官方题库"`、`"第三方平台"` |
| `author` | string | 作者 | `"张三"` |
| `date` | string | 创建日期 | `"2024-01-01"` |
| `version` | string | 版本号 | `"v1.0"` |
| `tags` | array | 自定义标签 | `["高频", "重点"]` |

**示例**：

```json
{
  "metadata": {
    "source": "2024年AI认证考试题库",
    "author": "AILearn Hub团队",
    "date": "2024-01-15",
    "version": "v1.0",
    "tags": ["高频", "必考", "新增"]
  }
}
```

**转换工具自动添加的元数据**：

使用 `convert_md_to_json.py` 或 `convert_docx_to_json.py` 转换时，会自动添加：

```json
{
  "metadata": {
    "source": "convert_md_to_json",  // 或 "convert_docx_to_json"
    "converted_at": "2024-01-15T10:30:00Z",  // 转换时间
    "original_file": "sample_quiz.md",  // 原始文件名
    "line_number": 15  // 原始文件中的行号
  }
}
```

---

## 题目类型详解

### 1. 单选题 (single_choice)

**特点**：
- 提供多个选项，只有一个正确答案
- `options` 必填，至少 2 个选项
- `correct_answer` 必须是单个选项键

**标准格式**：

```json
{
  "question_type": "single_choice",
  "content": "以下哪项是Python的特点？",
  "options": {
    "A": "编译型语言",
    "B": "解释型语言",
    "C": "汇编语言",
    "D": "机器语言"
  },
  "correct_answer": "B",
  "explanation": "Python是一种解释型语言，代码在运行时被逐行解释执行。",
  "knowledge_points": ["Python基础", "编程语言"],
  "difficulty": 1,
  "is_controversial": false,
  "metadata": {
    "source": "官方题库",
    "author": "AILearn Hub"
  }
}
```

**常见错误**：

❌ 错误：`correct_answer` 是数组
```json
{
  "correct_answer": ["B"]  // 应该是 "B"
}
```

❌ 错误：`correct_answer` 不在 `options` 中
```json
{
  "options": { "A": "选项A", "B": "选项B" },
  "correct_answer": "C"  // "C" 不存在
}
```

### 2. 多选题 (multiple_choice)

**特点**：
- 提供多个选项，有一个或多个正确答案
- `options` 必填，至少 2 个选项
- `correct_answer` 可以是逗号分隔的字符串或数组

**标准格式**：

```json
{
  "question_type": "multiple_choice",
  "content": "以下哪些是Python的应用领域？（多选）",
  "options": {
    "A": "Web开发",
    "B": "数据分析",
    "C": "机器学习",
    "D": "嵌入式系统"
  },
  "correct_answer": "A,B,C",  // 或 ["A", "B", "C"]
  "explanation": "Python在Web开发、数据分析、机器学习等领域广泛应用。",
  "knowledge_points": ["Python应用"],
  "difficulty": 3
}
```

**答案格式说明**：

支持三种格式（推荐使用格式 1）：

```json
// 格式 1：逗号分隔的字符串（推荐）
"correct_answer": "A,B,C"

// 格式 2：数组
"correct_answer": ["A", "B", "C"]

// 格式 3：带空格的逗号分隔（会自动清理）
"correct_answer": "A, B, C"
```

**自动排序**：
- 多选题答案会自动按字母排序
- 避免因答案顺序不同导致的重复检测问题

### 3. 判断题 (true_false)

**特点**：
- 只有两个选项："对"和"错"
- `options` 固定为 `{"A": "对", "B": "错"}`
- `correct_answer` 为 `"A"`（对）或 `"B"`（错）

**标准格式**：

```json
{
  "question_type": "true_false",
  "content": "Python是强类型语言。",
  "options": {
    "A": "对",
    "B": "错"
  },
  "correct_answer": "A",
  "explanation": "Python是强类型语言，不允许隐式类型转换。",
  "knowledge_points": ["Python基础"],
  "difficulty": 2
}
```

**答案格式**：

| 值 | 含义 | 说明 |
|-----|------|------|
| `"A"` | 对 | True / 正确 / √ |
| `"B"` | 错 | False / 错误 / × |

**在 Markdown 文本中**：
```
1、_[判断]_Python是强类型语言。
正确答案：对
```

转换后会自动处理为：
```json
{
  "correct_answer": "A"
}
```

### 4. 填空题 (fill_blank)

**特点**：
- 不需要 `options` 字段
- `correct_answer` 为任意字符串
- 可以设置多个正确答案（用 `|` 分隔）

**标准格式**：

```json
{
  "question_type": "fill_blank",
  "content": "Python中用于定义函数的关键字是____。",
  "correct_answer": "def",
  "explanation": "Python使用`def`关键字定义函数。",
  "knowledge_points": ["Python基础"],
  "difficulty": 1
}
```

**多答案格式**：

如果题目有多个可接受的正确答案：

```json
{
  "content": "Python中用于定义函数的关键字是____或____。",
  "correct_answer": "def|function"
}
```

用户输入任一答案都算正确。

### 5. 问答题 (essay)

**特点**：
- 不需要 `options` 字段
- `correct_answer` 为任意字符串（标准答案）
- 需要人工评分或使用 AI 评分

**标准格式**：

```json
{
  "question_type": "essay",
  "content": "请简述Python中列表和元组的区别。",
  "correct_answer": "列表是可变的，用[]定义；元组是不可变的，用()定义。",
  "explanation": "列表可以修改元素，元组创建后不可修改。",
  "knowledge_points": ["Python数据结构"],
  "difficulty": 4
}
```

**注意**：
- 问答题通常用于开放性问题
- 答案可以较长（建议不超过 5000 字符）
- 前端需要实现人工评分或 AI 评分功能

---

## 完整示例

### 示例 1：混合题型数组

```json
[
  {
    "question_type": "single_choice",
    "content": "以下哪项是Python的特点？",
    "options": {
      "A": "编译型语言",
      "B": "解释型语言",
      "C": "汇编语言",
      "D": "机器语言"
    },
    "correct_answer": "B",
    "explanation": "Python是一种解释型语言，代码在运行时被逐行解释执行。",
    "knowledge_points": ["Python基础", "编程语言"],
    "difficulty": 1,
    "metadata": {
      "source": "官方题库",
      "version": "v1.0"
    }
  },
  {
    "question_type": "multiple_choice",
    "content": "以下哪些是Python的应用领域？",
    "options": {
      "A": "Web开发",
      "B": "数据分析",
      "C": "机器学习",
      "D": "嵌入式系统"
    },
    "correct_answer": ["A", "B", "C"],
    "explanation": "Python在Web、数据分析、机器学习等领域广泛应用。",
    "knowledge_points": ["Python应用"],
    "difficulty": 3
  },
  {
    "question_type": "true_false",
    "content": "Python是强类型语言。",
    "options": {
      "A": "对",
      "B": "错"
    },
    "correct_answer": "A",
    "explanation": "Python是强类型语言，不允许隐式类型转换。",
    "knowledge_points": ["Python基础"],
    "difficulty": 2
  },
  {
    "question_type": "fill_blank",
    "content": "Python中用于定义函数的关键字是____。",
    "correct_answer": "def",
    "explanation": "Python使用`def`关键字定义函数。",
    "knowledge_points": ["Python基础"],
    "difficulty": 1
  },
  {
    "question_type": "essay",
    "content": "请简述Python中列表和元组的区别。",
    "correct_answer": "列表是可变的，用[]定义；元组是不可变的，用()定义。",
    "explanation": "列表可以修改元素，元组创建后不可修改。",
    "knowledge_points": ["Python数据结构"],
    "difficulty": 4
  }
]
```

### 示例 2：带元数据的题目

```json
{
  "question_type": "single_choice",
  "content": "在机器学习中，监督学习的特点是什么？",
  "options": {
    "A": "无标签数据训练",
    "B": "有标签数据训练",
    "C": "无监督聚类",
    "D": "强化学习"
  },
  "correct_answer": "B",
  "explanation": "监督学习使用有标签的数据进行训练，学习输入和输出之间的映射关系。",
  "knowledge_points": ["机器学习", "监督学习"],
  "difficulty": 2,
  "is_controversial": false,
  "metadata": {
    "source": "AILearn Hub官方题库",
    "author": "AI教育团队",
    "date": "2024-01-15",
    "version": "v2.1",
    "tags": ["必考", "高频", "重点"],
    "related_topics": ["无监督学习", "半监督学习"],
    "exam_year": 2024,
    "difficulty_origin": "中等"
  }
}
```

---

## 格式验证规则

### 必填字段验证

系统会验证以下必填字段是否存在且非空：

1. ✅ `question_type` - 题目类型
2. ✅ `content` - 题目内容
3. ✅ `correct_answer` - 正确答案

**验证失败示例**：

❌ 缺少 `question_type`：
```json
{
  "content": "题目内容",
  "correct_answer": "A"
  // 缺少 question_type
}
```

❌ `content` 为空：
```json
{
  "question_type": "single_choice",
  "content": "",  // 空字符串
  "correct_answer": "A"
}
```

### 选项格式验证

对于选择题（`single_choice`、`multiple_choice`、`true_false`）：

**验证规则**：

1. ✅ `options` 字段必须提供
2. ✅ `options` 必须是对象（键值对）
3. ✅ 至少有 2 个选项
4. ✅ `correct_answer` 必须是 `options` 中存在的键

**验证失败示例**：

❌ 缺少 `options`：
```json
{
  "question_type": "single_choice",
  "content": "题目",
  "correct_answer": "A"
  // 缺少 options
}
```

❌ `correct_answer` 不存在：
```json
{
  "question_type": "single_choice",
  "content": "题目",
  "options": {
    "A": "选项A",
    "B": "选项B"
  },
  "correct_answer": "C"  // "C" 不存在
}
```

### 答案格式验证

**根据题目类型验证答案格式**：

| 题目类型 | `correct_answer` 格式要求 |
|---------|----------------------|
| `single_choice` | 字符串，单个选项键（如 `"A"`） |
| `multiple_choice` | 字符串（逗号分隔）或数组（如 `"A,C"` 或 `["A", "C"]`） |
| `true_false` | 字符串 `"A"`（对）或 `"B"`（错） |
| `fill_blank` | 字符串 |
| `essay` | 字符串 |

**验证失败示例**：

❌ 单选题答案为数组：
```json
{
  "question_type": "single_choice",
  "correct_answer": ["A"]  // 应该是 "A"
}
```

❌ 多选题答案包含不存在的选项：
```json
{
  "question_type": "multiple_choice",
  "options": {
    "A": "选项A",
    "B": "选项B",
    "C": "选项C"
  },
  "correct_answer": "A,B,D"  // "D" 不存在
}
```

### 重复检测

**检测条件**：

系统通过以下字段组合检测重复题目：

1. `content` - 题目内容
2. `correct_answer` - 正确答案
3. `course_id` - 课程 ID（由导入脚本自动设置）

**行为**：

- 如果检测到重复，该题目将被跳过（不导入）
- 导入报告会列出所有被跳过的重复题目

**避免重复**：

- 相同的题目内容可以有不同的答案（例如不同版本的试题）
- 如果需要更新题目，先删除旧题目再导入新题目

---

## 扩展指南

### 如何自定义字段

#### 方式 1：使用 `metadata` 字段（推荐）

**优势**：
- 不影响现有导入逻辑
- 不会破坏格式兼容性
- 易于扩展和维护

**示例**：

```json
{
  "question_type": "single_choice",
  "content": "题目内容",
  "options": {
    "A": "选项A",
    "B": "选项B"
  },
  "correct_answer": "A",
  "metadata": {
    // 自定义字段放在这里
    "custom_field_1": "自定义值1",
    "custom_field_2": 123,
    "custom_array": ["值1", "值2"],
    "custom_object": {
      "nested": "嵌套值"
    },
    "exam_statistics": {
      "attempt_count": 1000,
      "correct_rate": 0.85,
      "difficulty_rating": 4.5
    }
  }
}
```

#### 方式 2：修改核心格式（需要代码修改）

**适用场景**：
- 需要所有题目都包含的新字段
- 需要在前端和后端都支持的新功能

**步骤**：

1. **修改数据库模型**（`src/backend/app/models/question.py`）：

```python
# 添加新字段
class Question(Base):
    # ... 现有字段 ...

    custom_field = Column(String, nullable=True)  # 新增字段
```

2. **修改导入脚本**（`scripts/import_questions.py`）：

```python
# 添加字段读取和验证
custom_field = question_data.get("custom_field")
if custom_field:
    question.custom_field = custom_field
```

3. **修改前端 API Client**（`src/frontend/lib/api.ts`）：

```typescript
// 在 Question 类型中添加新字段
export interface Question {
  // ... 现有字段 ...
  custom_field?: string;  // 新增字段
}
```

4. **更新本文档**，记录新字段的规范

### 如何添加新的题目类型

**步骤**：

1. **在 `question_type` 枚举中添加新类型**：

```json
["single_choice", "multiple_choice", "true_false", "fill_blank", "essay", "new_type"]
```

2. **修改数据库模型**（`src/backend/app/models/question.py`）：

```python
# 添加新类型的特定字段
class Question(Base):
    # ... 现有字段 ...
    new_type_field = Column(String, nullable=True)  # 新类型专用字段
```

3. **修改导入脚本**（`scripts/import_questions.py`）：

```python
# 添加新类型的验证逻辑
if question_type == "new_type":
    # 验证新类型必需的字段
    if not question_data.get("new_type_field"):
        raise ValueError("new_type requires new_type_field")
```

4. **修改前端渲染组件**（`src/frontend/components/`）：

```typescript
// 添加新类型的渲染逻辑
function QuestionRenderer({ question }: { question: Question }) {
  switch (question.question_type) {
    case "single_choice":
      return <SingleChoiceQuestion question={question} />;
    case "new_type":
      return <NewTypeQuestion question={question} />;  // 新类型组件
    // ... 其他类型 ...
  }
}
```

5. **更新本文档**，添加新类型的规范说明

---

## 常见问题

### Q1: 如何导入多选题的答案？

**A**: 使用逗号分隔的字符串格式（推荐）：

```json
{
  "question_type": "multiple_choice",
  "options": { "A": "选项A", "B": "选项B", "C": "选项C" },
  "correct_answer": "A,B,C"  // 推荐
}

// 或者使用数组格式
{
  "correct_answer": ["A", "B", "C"]
}
```

系统会自动对答案按字母排序，避免顺序问题。

### Q2: 选项的键名必须是 A、B、C 吗？

**A**: 不是。选项的键名可以是任意字符串，但建议使用字母（A、B、C、D）以便于阅读。

**自定义键名示例**：

```json
{
  "options": {
    "选项1": "内容1",
    "选项2": "内容2",
    "选项3": "内容3"
  },
  "correct_answer": "选项1"
}
```

**注意**：
- 自定义键名可能会影响某些前端组件的显示
- 转换工具（`convert_md_to_json.py`）默认只支持 A、B、C、D

### Q3: 如何处理有多个正确答案的题目？

**A**: 对于多选题，在 `correct_answer` 中列出所有正确答案：

```json
{
  "question_type": "multiple_choice",
  "options": {
    "A": "选项A",
    "B": "选项B",
    "C": "选项C",
    "D": "选项D"
  },
  "correct_answer": "A,C,D"  // 三个选项都正确
}
```

对于填空题，使用 `|` 分隔多个可接受答案：

```json
{
  "question_type": "fill_blank",
  "content": "Python中用于定义列表的关键字是____或____。",
  "correct_answer": "list|[]"  // 两个答案都正确
}
```

### Q4: 判断题如何设置？

**A**: 按照标准格式设置：

```json
{
  "question_type": "true_false",
  "content": "Python是强类型语言。",
  "options": {
    "A": "对",
    "B": "错"
  },
  "correct_answer": "A"  // "A" = 对，"B" = 错
}
```

在 Markdown 文本中，可以写：
```
1、_[判断]_Python是强类型语言。
正确答案：对  // 或 "√"、"A"
```

转换工具会自动处理为 `"A"`。

### Q5: 如何标记题目为有争议？

**A**: 设置 `is_controversial` 字段为 `true`：

```json
{
  "question_type": "single_choice",
  "content": "题目内容",
  "correct_answer": "A",
  "is_controversial": true  // 标记为有争议
}
```

有争议的题目可能需要人工复核。

### Q6: 可以在 metadata 中存储什么数据？

**A**: 任意 JSON 兼容的数据，包括：

- **字符串**：来源、作者、创建日期
- **数字**：版本号、分数、统计值
- **数组**：标签、相关主题
- **对象**：嵌套的元数据结构

**示例**：

```json
{
  "metadata": {
    "source": "官方题库",
    "author": "张三",
    "date": "2024-01-15",
    "version": "v1.0",
    "tags": ["高频", "必考"],
    "statistics": {
      "attempt_count": 1000,
      "correct_rate": 0.85
    }
  }
}
```

### Q7: 如何从 Markdown 或 Word 文档转换为 JSON？

**A**: 使用项目提供的转换工具：

**Markdown 转 JSON**：

```bash
cd scripts
uv run python convert_md_to_json.py -f sample_quiz.md
```

**Word 转 JSON**：

```bash
cd scripts
uv run python convert_docx_to_json.py -i exam_questions.docx
```

详细使用说明请参考 [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md)。

### Q8: 如何处理题目中的数学公式？

**A**: 使用 LaTeX 格式：

- **行内公式**：用 `$` 包裹，如 `$E=mc^2$`
- **块级公式**：用 `$$` 包裹，如 `$$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$$`

**示例**：

```json
{
  "content": "根据质能方程，能量和质量的换算公式是？",
  "options": {
    "A": "$E=mc$",
    "B": "$E=mc^2$",
    "C": "$E=m/c^2$",
    "D": "$E=m^2c$"
  },
  "correct_answer": "B",
  "explanation": "根据爱因斯坦的质能方程，$E=mc^2$。"
}
```

前端会使用 KaTeX 渲染这些公式。

### Q9: 如何批量导入题目？

**A**: 将多个题目放在一个数组中：

```json
[
  { "question_type": "single_choice", ... },
  { "question_type": "multiple_choice", ... },
  { "question_type": "true_false", ... }
]
```

然后使用 `import_questions.py` 导入：

```bash
cd scripts
uv run python import_questions.py \
  data/output/all_questions.json \
  --course-code ai_cert_exam
```

### Q10: 导入失败时如何排查问题？

**A**: 按照以下步骤排查：

1. **验证 JSON 格式**：
   ```bash
   # 使用 Python 验证
   python -c "import json; json.load(open('your_file.json'))"
   ```

2. **检查必填字段**：
   - `question_type` 是否存在且为有效值
   - `content` 是否非空
   - `correct_answer` 是否符合题目类型

3. **检查选择题的 `options`**：
   - 是否存在且为对象格式
   - `correct_answer` 是否在 `options` 中

4. **查看导入报告**：
   - 脚本会输出详细的错误信息
   - 检查是否有字段验证失败的题目

5. **使用样本测试**：
   - 先用少量题目测试导入
   - 确认格式正确后再批量导入

---

## 格式转换工具

### Markdown 转 JSON (`convert_md_to_json.py`)

**功能**：将 Markdown 格式的题库转换为标准 JSON 格式

**使用方法**：

```bash
cd scripts
uv run python convert_md_to_json.py -f sample_quiz.md
```

**支持的 Markdown 格式**：

```
1、_[单选]_题目内容
- A: 选项A
- B: 选项B
正确答案：A
解析：解析内容
```

**输出文件**：
- `sampleQuiz.json` - JSON 格式
- `sampleQuiz.csv` - CSV 格式（用于手动编辑）
- `sampleQuiz_conversion_report.md` - 转换报告

详细说明请参考 [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md)。

### Word 转 JSON (`convert_docx_to_json.py`)

**功能**：将 Word 文档（.docx）转换为标准 JSON 格式

**使用方法**：

```bash
cd scripts
uv run python convert_docx_to_json.py -i exam_questions.docx
```

**Word 文档格式要求**：
- 章节标题：`一、单选题`、`二、多选题`、`三、判断题`
- 题目格式：`1、题目内容`
- 选项格式：`A. 选项内容`
- **正确答案必须用红色字体标记**

详细说明请参考 [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md)。

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 2.0 | 2024-01-22 | 重新组织文档结构，强调格式规范和扩展指南 |
| 1.0 | 2024-01-20 | 初始版本，定义基础题目导入格式 |

---

## 相关文档

- [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md) - 脚本使用手册，详细的转换和导入步骤
- [../schema.sql](../schema.sql) - 数据库表结构定义
- [../src/backend/README.md](../src/backend/README.md) - 后端开发文档

---

## 支持与反馈

如果您在使用本格式规范时遇到问题或有改进建议，请：

1. 查阅 [常见问题](#常见问题) 部分
2. 参考 [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md) 获取详细使用说明
3. 提交 Issue 或 Pull Request

---

**最后更新**：2024-01-22
**维护者**：AILearn Hub Team
