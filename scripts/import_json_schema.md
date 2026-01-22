# 题目导入 JSON 格式说明

本文档定义了用于导入题目数据的 JSON 格式规范，所有导入脚本（如 `import_questions.py`）都应遵循此格式。

---

## 概述

- **支持格式**：单个题目对象或题目数组
- **文件编码**：UTF-8
- **用途**：导入题目到指定课程，可选创建题集
- **数据来源**：可以从文本格式（如 vault_sample 的 .md 文件）通过 `convert_questions.py` 转换为标准 JSON 格式

---

## 数据结构

### 0. 原始文本格式（供参考）

在转换为 JSON 之前，题目可能以文本格式存储（如 Markdown 文件）。`convert_questions.py` 脚本可以将这些文本格式转换为标准 JSON 格式。

#### 文本格式规范

**基本结构：**

```
数字、_[题型]_题目内容
- A: 选项内容
- B: 选项内容
- C: 选项内容
- D: 选项内容
正确答案：A
解析：答案解析内容
```

**示例：**

```
1、_[单选]_Python是一种解释型语言，以下哪项是其特点？
- A: 编译型语言
- B: 解释型语言
- C: 汇编语言
- D: 机器语言
正确答案：B
解析：Python是一种解释型语言，代码在运行时被逐行解释执行。
```

#### 支持的题型表示

| 文本格式 | JSON 格式 | 说明 |
|----------|-----------|------|
| `_[单选]_` | `single_choice` | 单选题 |
| `_[多选]_` | `multiple_choice` | 多选题 |
| `_[判断]_` | `true_false` | 判断题 |

#### 选项格式

- **标准格式**：`- A: 选项内容`（短横线 + 空格 + 选项键 + 冒号 + 空格 + 内容）
- **支持的键**：A, B, C, D
- **判断题**：无需手动提供选项，转换后自动添加 `options: {"A": "对", "B": "错"}`

#### 答案格式

| 题型 | 文本格式 | JSON 格式 | 转换规则 |
|------|----------|-----------|----------|
| 单选题 | `正确答案：B` | `"B"` | 直接使用字母，确保大写 |
| 多选题 | `正确答案：A,C,D` | `"A,C"` | 逗号分隔，字母排序 |
| 判断题 | `正确答案：对` 或 `正确答案：√` | `"A"` | 对/√/A → A；错/×/B → B |

**多选题答案变体支持：**

- 逗号分隔：`A,C,D`
- 中文逗号：`A，C，D`
- 混合空格：`A, C , D`

转换后会标准化为 `A,C,D`（字母排序）。

#### 解析格式

- **标准格式**：`解析：内容`
- **可选**：题目可以没有解析

#### 题干提取规则

题干 = 从题型标记后到"正确答案"之前的内容（不包含选项）。

**转换示例：**

```
原始文本：
1、_[单选]_Python是一种解释型语言。
- A: 编译型
- B: 解释型
正确答案：B

转换后题干：
"Python是一种解释型语言。"
```

#### 文本转换工具

使用 `convert_questions.py` 脚本转换：

```bash
cd src/scripts
uv run python convert_questions.py
```

转换后的文件保存在 `src/data/converted/` 目录：
- `题库1.json` - 单个题库的 JSON 文件
- `all_questions.json` - 合并所有题库的 JSON 文件
- `conversion_report.md` - 转换报告

---

### 1. 题目对象 (Question Object)

#### 必填字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `question_type` | string | 题目类型 | `"single_choice"`, `"multiple_choice"`, `"true_false"`, `"fill_blank"`, `"essay"` |
| `content` | string | 题目内容 | `"以下哪项是Python的特点？"` |
| `correct_answer` | string | 正确答案 | `"A"` 或 `"A,C"` 或 `"True"` |

#### 可选字段

| 字段名 | 类型 | 说明 | 默认值 | 示例 |
|--------|------|------|--------|------|
| `id` | string | 题目唯一标识符（可选，未指定时自动生成） | 自动生成 | `"550e8400-e29b-41d4-a716-446655440000"` |
| `options` | object | 选项（选择题必填，其他题型可选） | `null` | `{"A": "选项A", "B": "选项B", ...}` |
| `explanation` | string | 解析/答案说明 | `null` | `"Python是一种解释型语言，语法简洁易学。"` |
| `knowledge_points` | array | 知识点标签 | `[]` | `["Python基础", "编程语言"]` |
| `difficulty` | integer | 难度等级 (1-5) | `2` | `1` (简单), `3` (中等), `5` (困难) |
| `is_controversial` | boolean | 是否有争议（标记为争议题目） | `false` | `false` 或 `true` |
| `metadata` | object | 额外元数据 | `{}` | `{"source": "官方题库", "author": "张三"}` |
| `vector_id` | string | 向量ID（用于向量检索） | `null` | `"vec_123456"` |
| `course_type` | string | 课程类型（用于标识题目所属课程类别，**导入时需通过 `--course-code` 参数指定实际课程**） | `"exam"` | `"exam"`, `"ml_basic"` |

---

## 题目类型详解

### 1. 单选题 (single_choice)

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
  "difficulty": 1
}
```

### 2. 多选题 (multiple_choice)

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
  "correct_answer": ["A", "B", "C"],
  "explanation": "Python在Web开发、数据分析、机器学习等领域广泛应用。",
  "knowledge_points": ["Python应用"],
  "difficulty": 3
}
```

### 3. 判断题 (true_false)

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

**注意**：
- 判断题需要提供 `options` 字段，固定为 `{"A": "对", "B": "错"}`
- `correct_answer` 为 `"A"`（对）或 `"B"`（错）
- 在文本格式中，答案可以是"对"、"√"、"A"（都转换为 "A"），或"错"、"×"、"B"（都转换为 "B"）

### 4. 填空题 (fill_blank)

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

### 5. 问答题/简答题 (essay)

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

---

## 完整示例

### 单个题目

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
    "author": "AI助手"
  }
}
```

### 题目数组

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
    "explanation": "Python是一种解释型语言。",
    "knowledge_points": ["Python基础"],
    "difficulty": 1
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
    "correct_answer": "A,C",
    "explanation": "Python在Web、数据分析、机器学习等领域广泛应用。",
    "knowledge_points": ["Python应用"],
    "difficulty": 3
  },
  {
    "question_type": "true_false",
    "content": "Python是强类型语言。",
    "correct_answer": "True",
    "explanation": "Python是强类型语言，不允许隐式类型转换。",
    "knowledge_points": ["Python基础"],
    "difficulty": 2
  }
]
```

---

## 字段约束说明

### question_type（题目类型）

支持的类型：

| 类型值 | 说明 | 选项格式 | 答案格式 |
|--------|------|----------|----------|
| `single_choice` | 单选题 | `{"A": "选项A", "B": "选项B", ...}` | `"A"` |
| `multiple_choice` | 多选题 | `{"A": "选项A", "B": "选项B", ...}` | `"A,C"` 或 `["A", "C"]` |
| `true_false` | 判断题 | `{"A": "对", "B": "错"}` | `"A"`（对）或 `"B"`（错） |
| `fill_blank` | 填空题 | 不需要 | 任意字符串 |
| `essay` | 问答题 | 不需要 | 任意字符串 |

### difficulty（难度等级）

| 等级 | 说明 |
|------|------|
| 1 | 简单 |
| 2 | 较简单 |
| 3 | 中等 |
| 4 | 较难 |
| 5 | 困难 |

### knowledge_points（知识点）

- 类型：字符串数组
- 用途：用于题目标签和筛选
- 示例：`["Python基础", "数据结构", "算法"]`

### metadata（额外元数据）

- 类型：对象
- 用途：存储自定义扩展信息
- 示例：`{"source": "官方题库", "author": "张三", "date": "2024-01-01"}`

**通过 convert_questions.py 转换时自动添加的元数据：**

```json
{
  "source": "vault_sample",
  "vault_no": "1",
  "quiz_no": "1"
}
```

- `source`: 数据来源标识（如 "vault_sample"）
- `vault_no`: 题库编号
- `quiz_no`: 题目在题库中的编号

---

## CSV 格式说明

`convert_questions.py` 脚本还可以生成 CSV 格式的题目文件，适合在表格编辑器中手动编辑。

### CSV 字段

| 字段名 | 说明 | 必填 |
|--------|------|------|
| `course_type` | 课程类型 | 是 |
| `question_type` | 题目类型 | 是 |
| `content` | 题目内容 | 是 |
| `option_a` | 选项A（选择题必填） | 否 |
| `option_b` | 选项B（选择题必填） | 否 |
| `option_c` | 选项C（选择题必填） | 否 |
| `option_d` | 选项D（选择题必填） | 否 |
| `correct_answer` | 正确答案 | 是 |
| `explanation` | 解析 | 否 |
| `difficulty` | 难度 (1-5) | 否 |

### CSV 示例

```csv
course_type,question_type,content,option_a,option_b,option_c,option_d,correct_answer,explanation,difficulty
exam,single_choice,Python是一种解释型语言。,编译型,解释型,汇编语言,机器语言,B,Python是一种解释型语言。,1
exam,multiple_choice,以下哪些是Python的应用领域？,Web开发,数据分析,机器学习,嵌入式系统,"A,B,C",Python在Web、数据分析、机器学习等领域广泛应用。,3
exam,true_false,Python是强类型语言。,,,A,Python是强类型语言。,2
```

**注意**：CSV 文件目前不被 `import_questions.py` 直接导入，主要用于手动编辑后通过工具转换为 JSON 格式。

---

## 导入行为说明

### 1. 重复检测

系统通过以下字段检测重复题目：
- `content`（题目内容）
- `correct_answer`（正确答案）
- `course_id`（课程ID，由脚本自动设置）

如果检测到重复，该题目将被跳过（不导入）。

### 2. ID 生成

- 如果 JSON 中未提供 `id`，系统将自动生成唯一的 ID
- 如果提供了 `id`，将使用该 ID（需确保唯一性）

### 3. 题集创建（可选）

如果导入时指定了 `--question-set-code` 和 `--question-set-name` 参数：

- 系统将创建一个新的题集，包含本次导入的所有题目
- 如果题集已存在，将追加新题目到该题集

---

## 从文本格式到 JSON 格式的字段映射

| 文本格式字段 | JSON 字段 | 说明 |
|-------------|-----------|------|
| `_[单选]_` / `_[多选]_` / `_[判断]_` | `question_type` | 题型映射：`单选`→`single_choice`, `多选`→`multiple_choice`, `判断`→`true_false` |
| 题干（不包含选项） | `content` | 清理后的题目内容 |
| `- A: xxx` | `options.A` | 选项内容 |
| `- B: xxx` | `options.B` | 选项内容 |
| `- C: xxx` | `options.C` | 选项内容 |
| `- D: xxx` | `options.D` | 选项内容 |
| `正确答案：xxx` | `correct_answer` | 答案，多选题转为逗号分隔的字符串 |
| `解析：xxx` | `explanation` | 解析内容 |
| - | `difficulty` | 默认值为 2 |
| - | `knowledge_points` | 默认为空数组 `[]` |
| 文件名中的题库编号 | `metadata.vault_no` | 自动提取 |
| 题目编号 | `metadata.quiz_no` | 自动提取 |
| - | `metadata.source` | 固定为 `"vault_sample"` |

---

## 格式变体支持

### 题型标识变体

| 标准格式 | 支持的变体 |
|----------|-----------|
| `_[单选]_` | `_【单选】_`、`[单选题]`、`（单选题）` |
| `_[多选]_` | `_【多选】_`、`[多选题]`、`（多选题）` |
| `_[判断]_` | `_【判断】_`、`[判断题]`、`（判断题）` |

**注意**：`convert_questions.py` 目前只支持 `_[单选]_`、`_[多选]_`、`_[判断]_` 格式。如需支持其他变体，需修改脚本的正则表达式。

### 答案标识变体

| 标准格式 | 支持的变体 |
|----------|-----------|
| `正确答案：` | `正确选项：`、`答案：` |
| `解析：` | `答案解析：`、`【解析】：` |

### 选项标识变体

| 标准格式 | 支持的变体 |
|----------|-----------|
| `- A: xxx` | `A. xxx`、`A、xxx`、`A) xxx` |

**注意**：`convert_questions.py` 目前只支持 `- A: xxx` 格式。

### 判断题答案变体

| 标准格式 | 支持的变体 |
|----------|-----------|
| `对` | `√`、`A`、`正确`、`True` |
| `错` | `×`、`B`、`错误`、`False` |

### 空格处理

- 不间断空格 `\u00A0` 会被自动替换为普通空格
- 多余空格和空行会被自动清理
- 中文逗号 `，` 会被替换为英文逗号 `,`

---

## 验证规则

### 必填字段验证

以下字段必须存在且非空：
- `question_type`
- `content`
- `correct_answer`

如果缺少必填字段，该题目将被跳过并记录错误。

### 选项格式验证

对于选择题（`single_choice`、`multiple_choice`、`true_false`）：

- `single_choice`、`multiple_choice`：`options` 字段必须提供，必须是对象格式：`{"A": "选项A", "B": "选项B", ...}`
- `true_false`：`options` 字段必须提供，固定格式：`{"A": "对", "B": "错"}`
- `correct_answer` 必须是 `options` 中存在的键

### 答案格式验证

| 题目类型 | `correct_answer` 格式 |
|----------|----------------------|
| `single_choice` | 字符串，如 `"A"` |
| `multiple_choice` | 字符串（逗号分隔）或数组，如 `"A,C"` 或 `["A", "C"]` |
| `true_false` | 字符串 `"A"`（对/True）或 `"B"`（错/False） |
| `fill_blank` | 任意字符串 |
| `essay` | 任意字符串 |

---

## 扩展指南

### 添加新题目类型

如果需要支持新的题目类型：

1. 在 `question_type` 枚举中添加新类型
2. 在验证逻辑中添加对应的格式检查
3. 在前端组件中添加对应的渲染逻辑
4. 更新本文档

### 添加新字段

如果需要添加新的自定义字段：

1. 在 JSON 的 `metadata` 对象中添加（推荐，不影响现有逻辑）
2. 或者修改数据库模型和导入脚本（需要修改代码）

---

## 常见问题

### Q1: 如何导入多选题的答案？

**A**: 使用逗号分隔的字符串格式，如 `"correct_answer": "A,C"`。

在文本格式中，使用逗号分隔，如 `正确答案：A,C,D`，转换工具会自动标准化（字母排序）。

### Q2: 选项的键名必须是 A、B、C 吗？

**A**: 不是。选项的键名可以是任意字符串，如 `"选项1"`、`"选项2"`，但建议使用字母（A、B、C）以便于阅读。

在文本格式中，目前仅支持 A、B、C、D。

### Q3: 判断题如何设置？

**A**: `question_type` 设置为 `"true_false"`，`options` 固定为 `{"A": "对", "B": "错"}`，`correct_answer` 为 `"A"`（对）或 `"B"`（错）。

在文本格式中，无需手动提供选项，转换后会自动添加。答案可以是"对"、"√"、"A"（都转换为 "A"），或"错"、"×"、"B"（都转换为 "B"）。

### Q4: 如何标记题目为有争议？

**A**: 设置 `"is_controversial": true`。

### Q5: 可以在 metadata 中存储什么数据？

**A**: 任意 JSON 兼容的数据，如来源、作者、创建日期等。

通过 `convert_questions.py` 转换时，会自动添加 `source`、`vault_no`、`quiz_no` 字段。

### Q6: 如何从文本格式转换为 JSON 格式？

**A**: 使用 `convert_questions.py` 脚本：

```bash
cd src/scripts
uv run python convert_questions.py
```

转换后的文件会保存在 `src/data/converted/` 目录下。

### Q7: 文本格式的题目结构有什么要求？

**A**: 必须满足以下结构：

```
数字、_[题型]_题目内容
- A: 选项A
- B: 选项B
正确答案：A
解析：解析内容
```

- 题目以 `数字、` 开头
- 题型格式为 `_[单选]_`、`_[多选]_`、`_[判断]_`
- 选项格式为 `- A: 内容`
- 答案格式为 `正确答案：A` 或 `正确选项：A`
- 解析格式为 `解析：内容`

### Q8: 如何支持其他文本格式变体？

**A**: 修改 `convert_questions.py` 中的正则表达式：

- 题型匹配：修改 `r'^(\d+)、\s*_\[(单选|多选|判断)\]_\s*(.*)'`
- 选项匹配：修改 `r'-\s*([A-D])[:：]\s*(.*?)(?=\n|$)'`
- 答案匹配：修改 `r'(?:正确答案|正确选项)：\s*(.*?)(?=\n\s*解析：|\s*$)'`

### Q9: 多选题的答案顺序重要吗？

**A**: 不重要。`convert_questions.py` 会自动对多选题答案按字母排序，避免顺序问题。

例如：
- 输入：`正确答案：C,A,D`
- 输出：`"A,C,D"`

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-01-20 | 初始版本，定义基础题目导入格式 |

---

## 相关文件

- `import_questions.py` - 题目导入脚本
- `convert_questions.py` - 格式转换工具
- `README.md` - 脚本使用说明
