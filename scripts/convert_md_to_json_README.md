# Markdown 题库转换脚本

## 简介

此脚本用于将 Markdown 格式的题库文件（如 `sampleQuiz.md`）转换为标准的 JSON/CSV 格式，以便导入数据库。

## 脚本特性

- 支持指定任意 Markdown 文件（默认: `sampleQuiz.md`）
- 自动识别题型：单选题、多选题、判断题
- 支持多种格式变体（详见"支持的格式"）
- 输出 JSON 和 CSV 两种格式
- 生成详细的转换报告

## 支持的格式

### 题型标题格式

脚本支持以下格式的题型标题：

```
单选题 （每题1分，共39道题）
单选题(每个1分，共39分)
多选题 （每题2分，共20道题）
判断题 （每题1分，共40道题）
```

✅ 脚本会自动忽略标题行，不需要精确匹配。

### 题目格式

#### 标准格式
```
1、 [单选] 题干内容
2、 [多选] 题干内容
3、 [判断] 题干内容
```

#### 变体格式
```
1、_单选_ 题干内容
2、单选题：题干内容
```

✅ 脚本支持多种格式变体。

### 选项格式

#### 标准格式
```
A：选项内容
B：选项内容
C：选项内容
D：选项内容
```

#### 带连字符格式
```
-  A：选项内容
-  B：选项内容
```

#### 带冒号格式
```
A: 选项内容
B: 选项内容
```

✅ 脚本支持以上所有格式。

### 答案格式

#### 标准格式
```
正确答案：B
```

#### 带用户答案格式
```
正确答案：B 你的答案：B
正确选项：错 你的选项：错
```

✅ 脚本会自动忽略"你的答案/你的选项"部分。

### 判断题特殊处理

判断题支持以下表示方式：
- "对"、"√"、"A" → 映射为选项 A
- "错"、"×"、"B" → 映射为选项 B

## 使用方法

### 运行转换脚本

```bash
cd scripts

# 使用默认文件名（sampleQuiz.md）
uv run python convert_md_to_json.py

# 指定文件名
uv run python convert_md_to_json.py -f my_questions.md

# 指定完整路径
uv run python convert_md_to_json.py -f my_questions.md -i /path/to/input -o /path/to/output
```

### 参数说明

- `-f` / `--file`: 输入文件名（默认: `sampleQuiz.md`）
- `-i` / `--input-dir`: 输入目录路径（默认: `scripts/data/input/`）
- `-o` / `--output-dir`: 输出目录路径（默认: `scripts/data/output/`）

### 输出文件

转换完成后，会在输出目录下生成：

- `{filename}.json` - JSON格式题目数据
- `{filename}.csv` - CSV格式题目数据
- `{filename}_conversion_report.md` - 转换报告

### 导入数据库

如果需要将转换后的题目导入数据库：

```bash
cd scripts
uv run python import_questions.py data/output/sampleQuiz.json --course-code ai_cert_exam
```

## 转换结果示例

假设有以下 Markdown 文件（`sampleQuiz.md`）：

```markdown
单选题 （每题1分，共39道题）

1、 [单选] 你让一些人对数据集进行标记...
 A：0.0%〔因为不可能做得比这更好〕
 B：0.3%(专家1的错误率〕
 C：0.4%〔0_3到0.5之间〕
 D：0.75%〔以上所有四个数字的平均值〕

正确答案：B 你的答案：B
解析："人类表现"的定义通常是指...

多选题 （每题2分，共20道题）

1、 [多选] 在典型的卷积神经网络中，你能看到的是？
 A：多个卷积层后面跟着的是一个池化层。
 B：多个池化层后面跟着的是一个卷积层。
 C：全连接层（FC)位于最后的几层。
 D：全连接层（FC)位于开始的几层。

正确答案：A,C 你的答案：A,B
解析：在典型的卷积神经网络中...

判断题 （每题1分，共40道题）

1、 [判断] 假如你正在应用一个滑动窗口分类器...
 A：对
 B：错

正确选项：错 你的选项：错
解析：增加步长会降低准确性...
```

### 输出统计

```
处理文件: sampleQuiz.md
   解析到 3 道题目
   题型分布:
     - 单选: 1题
     - 多选: 1题
     - 判断: 1题

✅ JSON文件已保存: /path/to/scripts/data/output/sampleQuiz.json
   总题数: 3
✅ CSV文件已保存: /path/to/scripts/data/output/sampleQuiz.csv
```

### JSON 数据格式示例

#### 单选题
```json
{
  "course_type": "exam",
  "question_type": "single_choice",
  "content": "你让一些人对数据集进行标记...",
  "options": {
    "A": "0.0%〔因为不可能做得比这更好〕",
    "B": "0.3%(专家1的错误率〕",
    "C": "0.4%〔0_3到0.5之间〕",
    "D": "0.75%〔以上所有四个数字的平均值〕"
  },
  "correct_answer": "B",
  "explanation": "\"人类表现\"的定义通常是指...",
  "difficulty": 2,
  "knowledge_points": [],
  "metadata": {
    "source": "vault_sample",
    "vault_no": "Quiz",
    "quiz_no": "1"
  }
}
```

#### 多选题
```json
{
  "course_type": "exam",
  "question_type": "multiple_choice",
  "content": "在典型的卷积神经网络中，你能看到的是？",
  "options": {
    "A": "多个卷积层后面跟着的是一个池化层。",
    "B": "多个池化层后面跟着的是一个卷积层。",
    "C": "全连接层（FC)位于最后的几层。",
    "D": "全连接层（FC)位于开始的几层。"
  },
  "correct_answer": "A,C",
  "explanation": "在典型的卷积神经网络中...",
  "difficulty": 2,
  "knowledge_points": [],
  "metadata": {
    "source": "vault_sample",
    "vault_no": "Quiz",
    "quiz_no": "1"
  }
}
```

#### 判断题
```json
{
  "course_type": "exam",
  "question_type": "true_false",
  "content": "假如你正在应用一个滑动窗口分类器...",
  "options": {
    "A": "对",
    "B": "错"
  },
  "correct_answer": "B",
  "explanation": "增加步长会降低准确性...",
  "difficulty": 2,
  "knowledge_points": [],
  "metadata": {
    "source": "vault_sample",
    "vault_no": "Quiz",
    "quiz_no": "1"
  }
}
```

## 技术细节

### 正则表达式关键模式

#### 题目分割
```python
# 按题型分组
type_sections = re.split(r'(单选题|多选题|判断题)\s*[（\(].*?[）\)]', quiz_text)

# 按题目分割
blocks = re.split(r'(?=\n\s*\d+、)', '\n' + section_content.strip())
```

#### 题号和题型匹配
```python
# 匹配：数字、 [类型] 题干
pattern = r'^(\d+)、\s*\[(单选|多选|判断)\]\s*(.*)'
```

#### 正确答案提取（忽略"你的答案"）
```python
# 匹配：正确答案/正确选项，忽略"你的答案/你的选项"
ans_match = re.search(r'(?:正确答案|正确选项)：\s*([^你的]+?)(?=你的[答案选项]|解析：|\s*$)', rest, re.DOTALL)
```

#### 选项提取（支持有/无连字符）
```python
# 匹配：A: 选项内容（支持中英文冒号）
option_pattern = r'\s*[A-D][:：]\s*(.*?)(?=\n|$)'
```

## 注意事项

1. **编码问题**：脚本会自动清理不间断空格（\u00A0），建议使用 UTF-8 编码
2. **多选题答案**：会按字母排序，避免乱序问题（如 "B,A" → "A,B"）
3. **判断题答案**：支持"对"/"错"/"√"/"×"/"A"/"B"等多种表示方式
4. **容错处理**：如果解析失败，会输出详细的错误信息，但不会中断整个转换过程
5. **默认值**：
   - 判断题默认选项：A=对, B=错
   - 默认难度：2
   - 默认课程类型：exam

## 扩展其他题库

如果要转换其他格式的题库文件，可以：

1. **查看脚本源码**：参考 `convert_md_to_json.py` 中的正则表达式模式
2. **调整正则表达式**：根据实际格式修改对应的正则模式
3. **使用通用脚本**：如果格式差异太大，考虑使用 `convert_questions.py` 脚本

## 常见问题

### 1. 解析结果为空

**可能原因：**
- 题型标题格式不匹配
- 题号格式不匹配
- 编码问题

**解决方法：**
- 检查文件是否使用 UTF-8 编码
- 确保题型标题包含"单选题"/"多选题"/"判断题"
- 确保题目以"数字、"开头

### 2. 答案解析错误

**可能原因：**
- 答案行格式不标准
- 特殊字符干扰

**解决方法：**
- 确保答案行包含"正确答案："或"正确选项："
- 检查是否有特殊字符（如不间断空格）

### 3. 选项解析错误

**可能原因：**
- 选项格式不符合要求
- 选项标签不是 A-D

**解决方法：**
- 确保选项标签为 A、B、C、D
- 检查选项格式是否包含冒号或中文冒号

## 相关脚本

- `convert_docx_to_json.py` - Word 文档转 JSON
- `convert_questions.py` - 通用的题库转换脚本
- `import_questions.py` - 题目导入数据库脚本
- `init_db.py` - 初始化数据库
- `init_course_data.py` - 初始化课程数据
