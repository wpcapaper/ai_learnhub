# 脚本使用手册

本手册提供了从数据准备到数据库导入的完整操作指南。

---

## 目录

- [环境准备](#环境准备)
- [完整初始化流程（一条龙服务）](#完整初始化流程一条龙服务)
- [普通题集导入流程](#普通题集导入流程)
- [考试模式固定题集导入流程](#考试模式固定题集导入流程)
- [常见问题](#常见问题)
- [附录：脚本说明](#附录脚本说明)

---

## 环境准备

### 1. 前置要求

确保已安装 Python 3.11+ 和 [uv](https://github.com/astral-sh/uv)：

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 安装依赖

```bash
cd scripts
uv sync
```

### 3. 目录结构

确保项目目录结构如下：

```
your-project/
├── scripts/              # 脚本目录
│   ├── data/             # 数据目录
│   │   ├── input/        # 输入数据（源文件）
│   │   │   ├── sample_quiz.md
│   │   │   └── exam_questions.docx
│   │   └── output/       # 输出数据（转换后的 JSON）
│   │       ├── sample_quiz.json
│   │       └── exam_questions.json
│   ├── init_db.py
│   ├── init_course_data.py
│   ├── import_questions.py
│   ├── convert_docx_to_json.py
│   ├── convert_md_to_json.py
│   ├── pyproject.toml
│   └── uv.lock
├── src/
│   └── backend/
│       └── app/
│           ├── models.py
│           ├── core/
│           │   ├── database.py
│           │   └── config.py
│           └── ...
```

**准备输入数据：**

将你的数据源文件放入 `scripts/data/input/` 目录：
- Markdown 文件（如 `sample_quiz.md`）
- Word 文档（如 `exam_questions.docx`）

---

## 完整初始化流程（一条龙服务）

### 场景说明

首次搭建环境，从零开始初始化数据库、创建课程、导入题库。

### 操作步骤

#### 步骤 1：初始化数据库表

```bash
cd scripts
uv run python init_db.py
```

**输出示例：**
```
初始化数据库...
完成！
```

#### 步骤 2：创建课程

```bash
uv run python init_course_data.py
```

**输出示例：**
```
🚀 Initializing course data...
📋 Creating database tables...
✅ Created 2 courses:
   - ai_cert_exam: AI认证考试
   - ml_basic: 机器学习基础
✅ Course data initialization completed!
```

**自定义课程：**

编辑 `init_course_data.py` 文件，在 `init_course_data()` 函数中添加课程：

```python
def init_course_data(db: Session):
    courses = [
        # 默认课程
        create_course(
            code="ai_cert_exam",
            title="AI认证考试",
            description="AIE55 AI认证考试题库",
            sort_order=1
        ),

        # 添加自定义课程
        create_course(
            code="my_custom_course",
            title="自定义课程",
            description="这是我的自定义课程",
            sort_order=3,
            difficulty_range=[1, 4]  # 可选参数
        ),
    ]
    # ... 其余代码
```

#### 步骤 3：导入题目数据

根据数据源类型选择不同的导入方式（详见后续章节）。

---

## 普通题集导入流程

### 场景说明

将题目导入为普通题集，用于日常刷题和艾宾浩斯学习。

**数据源格式：**
- Markdown 文件（如 `sample_quiz.md`）
- JSON 文件（标准格式）

### 流程 1：从 Markdown 转换并导入

#### 步骤 1：转换 Markdown 为 JSON

```bash
cd scripts
uv run python convert_md_to_json.py

# 指定文件名
uv run python convert_md_to_json.py -f my_questions.md

# 指定完整路径
uv run python convert_md_to_json.py -f my_questions.md -i /path/to/input -o /path/to/output
```

**参数说明：**
- `-f` / `--file`: 输入文件名（默认: `sample_quiz.md`）
- `-i` / `--input-dir`: 输入目录路径（默认: `scripts/data/input/`）
- `-o` / `--output-dir`: 输出目录路径（默认: `scripts/data/output/`）

**使用示例：**
```bash
# 使用默认文件名（sample_quiz.md）
uv run python convert_md_to_json.py

# 指定文件名
uv run python convert_md_to_json.py -f my_questions.md

# 指定完整路径
uv run python convert_md_to_json.py -f my_questions.md -i /path/to/input -o /path/to/output
```

**要求：**
- 确保 `scripts/data/input/sample_quiz.md` 文件存在
- 文件格式参考：`scripts/convert_md_to_json_README.md`

**输出文件：**
- `{output_dir}/{filename}.json` - JSON 格式
- `{output_dir}/{filename}.csv` - CSV 格式
- `{output_dir}/{filename}_conversion_report.md` - 转换报告

**输出示例：**
```
脚本目录: /path/to/scripts
输入目录: /path/to/scripts/data/input
输出目录: /path/to/scripts/data/output

处理文件: sample_quiz.md
   解析到 99 道题目
   题型分布:
     - 单选: 39题
     - 多选: 20题
     - 判断: 40题

✅ JSON文件已保存: /path/to/scripts/data/output/sample_quiz.json
   总题数: 99
✅ CSV文件已保存: /path/to/scripts/data/output/sample_quiz.csv

✅ 转换完成!

转换报告已保存: /path/to/scripts/data/output/sample_quiz_conversion_report.md

下一步:
  1. 检查转换结果: /path/to/scripts/data/output/sample_quiz.json
  2. 如需导入数据库，运行:
     cd /path/to/scripts
     uv run python import_questions.py data/output/sample_quiz.json
```

#### 步骤 2：导入 JSON 到数据库

```bash
uv run python import_questions.py \
  data/output/sample_quiz.json \
  --course-code ai_cert_exam
```

**参数说明：**
- `--json-file` / `-f`: JSON 文件路径（必填）
- `--course-code` / `-c`: 课程代码（必填）
- `--question-set-code` / `-s`: 题集代码（可选）
- `--question-set-name` / `-n`: 题集名称（可选）
- `--init-db` / `-i`: 初始化数据库表（首次使用）

**输出示例：**
```
从 ../data/converted/sample_quiz.json 导入题目...
✅ Imported 99 questions to course: AI认证考试 (ai_cert_exam)

导入完成！
  总题目数: 99
  成功导入: 99
  跳过: 0
  错误: 0
```

---

### 流程 2：直接导入 JSON 文件

如果已有标准格式的 JSON 文件，直接导入：

```bash
uv run python import_questions.py \
  /path/to/questions.json \
  --course-code ai_cert_exam
```

**JSON 格式示例：**

```json
[
  {
    "course_type": "exam",
    "question_type": "single_choice",
    "content": "题目内容",
    "options": {
      "A": "选项A",
      "B": "选项B",
      "C": "选项C",
      "D": "选项D"
    },
    "correct_answer": "B",
    "explanation": "解析内容",
    "difficulty": 2,
    "knowledge_points": [],
    "metadata": {
      "source": "custom"
    }
  }
]
```

---

## 考试模式固定题集导入流程

### 场景说明

将题目导入为固定题集，用于模拟考试模式。系统会按固定顺序出题，不会随机抽取。

**数据源格式：**
- Word 文档（.docx）
- 需要在文档中用**红色**标记正确答案

### 流程 1：从 DOCX 转换并导入

#### 步骤 1：转换 DOCX 为 JSON

```bash
cd scripts
uv run python convert_docx_to_json.py -i /path/to/questions.docx
```

**参数说明：**
- `-i` / `--input`: 输入 DOCX 文件路径（必填）
- `-o` / `--output`: 输出 JSON 文件路径（可选，默认：`../data/converted/{docx_filename}.json`）
- `-p` / `--placeholder-explanation`: 解析字段的占位符文本（默认：`暂无解析`）
- `-d` / `--default-difficulty`: 默认难度等级 1-5（默认：2）

**示例：**

```bash
# 使用默认输出路径（输出到 data/output/）
uv run python convert_docx_to_json.py -i data/input/exam_questions.docx

# 指定输出路径
uv run python convert_docx_to_json.py -i data/input/exam_questions.docx -o data/output/exam_set1.json

# 设置占位符和难度
uv run python convert_docx_to_json.py -i data/input/exam_questions.docx -p "解析待补充" -d 3
```

**输出示例：**
```
📖 正在解析: exam_questions.docx
✅ 解析完成!
  总题目数: 150
  单选题: 100
  多选题: 30
  判断题: 20

📄 已保存到: data/output/exam_questions.json
✅ JSON文件验证通过
```

**DOCX 文件格式要求：**

1. **章节标题**：`一、单选题`、`二、多选题`、`三、判断题`
2. **题目格式**：`1、题目内容`
3. **选项格式**：`A. 选项内容`
4. **正确答案**：用**红色字体**标记（支持多选题多选）

**示例：**

```
一、单选题

1、以下哪项是机器学习的主要特点？
A. 自动学习特征
B. 手工设计特征
C. 固定规则
D. 无需数据
```

选项中，用红色标记正确答案（如选项 A 标记为红色）。

#### 步骤 2：导入 JSON 为固定题集

```bash
uv run python import_questions.py \
  data/output/exam_questions.json \
  --course-code ai_cert_exam \
  --question-set-code exam_set1 \
  --question-set-name "2025年模拟考试题集"
```

**参数说明：**
- `--question-set-code`: 固定题集代码（必填）
- `--question-set-name`: 固定题集名称（必填）

**输出示例：**
```
从 ../data/converted/exam_questions.json 导入题目...
✅ Imported 150 questions to course: AI认证考试 (ai_cert_exam)
   Question set: exam_set1
✅ Created question set: 2025年模拟考试题集 with 150 questions

导入完成！
  总题目数: 150
  成功导入: 150
  跳过: 0
  错误: 0
```

---

## 常见问题

### 1. 导入时报错 "Course not found"

**原因：** 课程不存在，需要先创建课程。

**解决：**
```bash
# 创建课程
uv run python init_course_data.py

# 或编辑 init_course_data.py 添加自定义课程
```

### 2. DOCX 转换时未检测到红色答案

**原因：** Word 文档中的答案未用红色字体标记。

**解决：**
- 在 Word 中选中正确答案选项
- 设置字体颜色为红色（RGB: 255, 0, 0）
- 保存后重新转换

### 3. JSON 导入时跳过了所有题目

**原因：** 题目已存在（根据 content + correct_answer + course_id 判断）。

**解决：**
- 这是正常去重行为，如果需要重新导入，请先清空数据库
- 或修改 JSON 中的题目内容

### 4. Markdown 转换失败

**原因：** 文件格式不符合要求。

**解决：**
- 参考 `scripts/convert_md_to_json_README.md` 检查格式
- 确保题目格式为：`数字、 [题型] 题目内容`
- 确保选项格式为：` A：选项内容`

### 5. 如何重置数据库

```bash
cd scripts
uv run python clean_db.py
```

**警告：** 此操作会删除所有数据，需要二次确认。

---

## 附录：脚本说明

### init_db.py

**作用：** 初始化数据库表结构。

**使用：**
```bash
uv run python init_db.py
```

**说明：** 仅需首次运行，后续无需重复执行。

---

### init_course_data.py

**作用：** 创建默认课程。

**使用：**
```bash
uv run python init_course_data.py
```

**自定义课程：**

编辑脚本中的 `init_course_data()` 函数：

```python
def init_course_data(db: Session):
    courses = [
        create_course(
            code="course_code",
            title="课程标题",
            description="课程描述",
            sort_order=1,
            question_type_config={  # 可选
                "single_choice": 30,
                "multiple_choice": 10,
                "true_false": 10
            },
            difficulty_range=[1, 5]  # 可选
        ),
    ]
```

---

### import_questions.py

**作用：** 从 JSON 文件导入题目到数据库。

**使用：**
```bash
# 普通题集导入
uv run python import_questions.py -f questions.json -c ai_cert_exam

# 固定题集导入
uv run python import_questions.py \
  -f exam.json \
  -c ai_cert_exam \
  -s exam_set1 \
  -n "考试题集"

# 多文件导入（用逗号分隔）
uv run python import_questions.py -f file1.json,file2.json -c ai_cert_exam
```

---

### convert_md_to_json.py

**作用：** 将 Markdown 格式的题库转换为 JSON/CSV 格式。

**使用：**
```bash
# 使用默认文件名（sample_quiz.md）
uv run python convert_md_to_json.py

# 指定文件名
uv run python convert_md_to_json.py -f my_questions.md

# 指定完整路径
uv run python convert_md_to_json.py -f my_questions.md -i /path/to/input -o /path/to/output
```

**参数：**
- `-f` / `--file`: 输入文件名（默认: `sample_quiz.md`）
- `-i` / `--input-dir`: 输入目录路径（默认: `scripts/data/input/`）
- `-o` / `--output-dir`: 输出目录路径（默认: `scripts/data/output/`）

**说明：**
- 支持任意 Markdown 格式的题库文件
- 输出 JSON、CSV 格式及转换报告
- 文件格式参考：`scripts/convert_md_to_json_README.md`

---

### convert_docx_to_json.py

**作用：** 将 Word 文档转换为 JSON 格式。

**使用：**
```bash
uv run python convert_docx_to_json.py -i data/input/exam.docx -o data/output/exam.json
```

**说明：**
- 支持红色标记正确答案
- 自动识别题型（单选/多选/判断）
- 默认输出到 `data/output/` 目录

---

## 快速参考

### 完整流程（普通题集）

```bash
cd scripts

# 1. 初始化数据库
uv run python init_db.py

# 2. 创建课程
uv run python init_course_data.py

 # 3. 转换数据（使用默认文件名 sample_quiz.md）
uv run python convert_md_to_json.py

# 3.1 或指定文件名
uv run python convert_md_to_json.py -f my_questions.md

# 4. 导入题目
uv run python import_questions.py \
  data/output/sample_quiz.json \
  --course-code ai_cert_exam
```

### 完整流程（固定题集）

```bash
cd scripts

# 1. 初始化数据库
uv run python init_db.py

# 2. 创建课程
uv run python init_course_data.py

# 3. 转换数据
uv run python convert_docx_to_json.py -i data/input/exam.docx

# 4. 导入题目
uv run python import_questions.py \
  data/output/exam.docx.json \
  --course-code ai_cert_exam \
  --question-set-code exam_set1 \
  --question-set-name "考试题集"
```

---

## 联系支持

如有问题，请提交 Issue 或联系项目维护者。
