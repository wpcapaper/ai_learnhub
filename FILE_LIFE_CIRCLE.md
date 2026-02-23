# 课程转换导入完整生命周期

本文档描述课程从原始数据到最终入库的完整生命周期，包括各阶段字段生成时机。

---

## 设计原则

- **单一数据源**：课程内容始终存储在 `markdown_courses/{code}/`，不创建额外副本
- **目录名即标识**：`code` 作为目录名，确保文件系统层面的唯一性
- **数据库主键独立**：`id` 使用 UUID，与 `code` 解耦，用于数据库关联
- **版本通过后缀管理**：`python_basics` → `python_basics_v1` → `python_basics_v2`

---

## 阶段概览图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              课程转换导入生命周期                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [原始数据]           [转换阶段]              [输出阶段]           [入库阶段]     │
│                                                                                 │
│  raw_courses/         CoursePipeline         markdown_courses/    数据库        │
│  └─ {course_name}/    ──────────────►        └─ {code}/           ───────►      │
│     ├─ *.md           1. 扫描源文件              ├─ course.json    1. 检查重复   │
│     └─ *.ipynb        2. 转换格式                ├─ *.md           2. 生成 UUID  │
│                        3. 生成 course.json       └─ assets/        3. 写入数据  │
│                                                                                 │
│                              ↓ 章节重排（可选，独立流程）                          │
│                                                                                 │
│                      markdown_courses/{code}_v{N}/                              │
│                      └─ course.json  (含 origin, version)                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 阶段一：原始数据 (raw_courses/)

**触发条件**：管理员调用 `POST /api/admin/courses/convert/{course_name}`

**数据来源**：`raw_courses/{course_name}/` 目录

**重要说明**：
- 目录名作为**默认**的 `course_name`（可能包含中文、空格等）
- **不支持** `course.json`，即使存在也视为无效资料被过滤
- 只扫描 `.md`, `.ipynb` 文件

**产生的字段**：

| 字段 | 来源 | 说明 |
|------|------|------|
| `course_name` | 目录名 | 如 `Python基础`，用于生成 `code` |
| `source_files[]` | 扫描 | `.md`, `.ipynb` 文件列表 |

**文件结构**：

```
raw_courses/Python基础/
├── 01_简介.md
├── 02_变量.md
└── 03_函数.ipynb
```

---

## 阶段二：转换阶段 (CoursePipeline)

**处理类**：`CoursePipeline` (`src/backend/app/course_pipeline/pipeline.py`)

**重要**：此阶段**不进行章节重排**，保持原始顺序。

### 子阶段流程

#### 2.1 扫描源文件

```python
source_files = []  # 收集 *.md, *.ipynb 文件
for file_path in course_dir.rglob(ext):
    source_files.append(SourceFile.from_path(str(file_path)))
```

#### 2.2 格式转换

```python
converter = self.converter_registry.get_converter(source_file.content_type)
chapters = converter.convert(source_file, output_dir)
```

**产生的字段**：

| 字段 | 来源 | 说明 |
|------|------|------|
| `chapter.code` | 从文件名提取 | 如 `intro` |
| `chapter.title` | 文件标题 | 章节标题 |
| `chapter.content` | 转换结果 | Markdown 内容 |
| `chapter.file_name` | 生成 | 如 `01_简介.md` |

#### 2.3 生成 course_code

```python
def _generate_course_code(self, course_name: str) -> str:
    # 清理目录名，生成合法的 code
    code = re.sub(r'[^\w\u4e00-\u9fff-]', '_', course_name)
    code = re.sub(r'_+', '_', code).strip('_')
    return code.lower()
```

**示例**：`Python基础` → `python_基础` → `python_basics`（如果转拼音）或保留 `python_基础`

---

## 阶段三：输出阶段 (markdown_courses/)

**输出目录**：`markdown_courses/{code}/`

**注意**：首次转换不带版本号后缀。

**目录结构**：

```
markdown_courses/
├── python_basics/              # 首次转换
│   ├── course.json
│   ├── 01_简介.md
│   ├── 02_变量.md
│   ├── 03_函数.md
│   └── assets/
│       └── diagram.png
│
└── python_basics_v1/           # 章节重排后（可选）
    ├── course.json             # 含 origin, version 字段
    ├── 01_introduction.md      # 重排后的章节
    └── assets/
```

### course.json 结构

**首次转换（无版本）**：

```json
{
  "code": "python_basics",
  "title": "Python基础",
  "description": "从 raw_courses/Python基础 导入",
  "chapters": [
    {
      "code": "intro",
      "title": "简介",
      "file": "01_简介.md",
      "sort_order": 1
    }
  ]
}
```

**章节重排后（带版本）**：

```json
{
  "code": "python_basics_v1",
  "origin": "python_basics",
  "version": 1,
  "title": "Python基础",
  "chapters": [...]
}
```

| 字段 | 说明 |
|------|------|
| `code` | 课程代码，目录名 |
| `origin` | 原始课程代码（仅重排后有） |
| `version` | 版本号，从 1 开始（仅重排后有） |

### 章节重排（可选，独立流程）

**触发条件**：管理员手动调用 `POST /api/admin/courses/reorder/{code}`

**处理逻辑**：
1. 读取现有 `markdown_courses/{code}/course.json`
2. 按规则重新排序章节
3. 检测现有版本，生成新版本号 N
4. 创建新目录 `{code}_v{N}`
5. 复制内容到新目录，更新 `course.json`

---

## 阶段四：入库阶段 (数据库)

**触发条件**：管理员调用 `POST /api/admin/markdown-courses/{code}/import`

**注意**：只支持单课程导入，不支持批量导入。

### 4.1 读取转换后的课程

```python
course_json = load_course_json(markdown_courses / code)
```

### 4.2 检查重复

```python
existing = db.query(Course).filter(Course.code == code).first()
if existing and not existing.is_deleted:
    raise HTTPException(400, "课程代码已存在")
```

### 4.3 生成数据库记录

```python
course = Course(
    id=str(uuid.uuid4()),        # UUID 主键，唯一标识
    code=code,                   # 目录名/课程代码
    title=course_json.get("title"),
    description=course_json.get("description"),
    course_type=course_json.get("course_type", "learning"),
    is_active=True,
    created_at=datetime.utcnow()
)
```

**产生字段**：

| 字段 | 来源 | 说明 |
|------|------|------|
| `id` | `uuid.uuid4()` | **数据库主键**，唯一标识 |
| `code` | 目录名 | 课程代码，可重复（多版本） |
| `title` | course.json | 课程标题 |
| `description` | course.json | 描述 |
| `course_type` | course.json 或默认 | 类型 |
| `is_active` | 默认 `True` | 是否启用 |
| `created_at` | `datetime.utcnow()` | 创建时间 |

### 4.4 提交事务

```python
db.commit()
```

---

## 字段生成时机汇总表

| 字段 | 阶段一 | 阶段二 | 阶段三 | 阶段四 |
|------|:------:|:------:|:------:|:------:|
| `course_name` | ✅ 目录名 | → | → | → 忽略 |
| `code` | - | ✅ 生成 | 目录名 | ✅ 从json读取 |
| `origin` | - | - | ✅ 章节重排时 | - |
| `version` | - | - | ✅ 章节重排时 | - |
| `id` (数据库主键) | - | - | - | ✅ UUID |
| `title` | - | ✅ 从源文件 | 写入json | ✅ 从json读取 |
| `description` | - | ✅ 默认值 | 写入json | ✅ 从json读取 |
| `is_active` | - | - | - | ✅ 默认 `True` |
| `created_at` | - | - | - | ✅ `datetime.utcnow()` |
| `chapter.code` | - | ✅ 从文件名 | 写入json | ✅ 从json读取 |
| `chapter.sort_order` | - | ✅ 原始顺序 | 可重排 | ✅ 从json读取 |

---

## 词云查询设计

词云文件始终存储在课程目录下，无论课程是否已导入都能访问。

### 查询逻辑

```python
# 待导入课程：用 code（目录名）
wordcloud_path = markdown_courses / code / "wordcloud.json"

# 已导入课程：用 id（UUID）→ 查 code → 再找文件
course = db.query(Course).filter(Course.id == id).first()
wordcloud_path = markdown_courses / course.code / "wordcloud.json"
```

### API 设计

| 端点 | 参数 | 场景 |
|------|------|------|
| `GET /api/courses/{id}/wordcloud` | `id` (UUID) | 已导入课程 |
| `GET /api/courses/code/{code}/wordcloud` | `code` | 待导入课程 |

---

## API 端点汇总

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/admin/courses/convert/{course_name}` | POST | 转换单个原始课程 |
| `/api/admin/courses/reorder/{code}` | POST | 章节重排（可选） |
| `/api/admin/markdown-courses/{code}/import` | POST | 导入单个已转换课程 |
| `/api/admin/database/courses/{id}/activate` | PUT | 启用/停用课程 |

**已移除**：
- ~~`POST /api/admin/courses/convert`~~（批量转换）
- ~~`POST /api/admin/courses/import`~~（批量导入）

---

## 数据模型定义

### Course 表结构

```python
class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    code = Column(String(50), nullable=False, index=True)  # 可重复
    title = Column(String(200), nullable=False)
    description = Column(Text)
    course_type = Column(String(20), nullable=False, index=True)
    cover_image = Column(String(500), nullable=True)
    default_exam_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
```

---

## 目录结构总览

```
raw_courses/                      # 原始数据
├── Python基础/
│   ├── 01_简介.md
│   └── 02_变量.ipynb
└── ...

markdown_courses/                 # 转换产物（单一数据源）
├── python_basics/               # 首次转换
│   ├── course.json
│   ├── *.md
│   ├── assets/
│   └── wordcloud.json           # 词云（可选）
├── python_basics_v1/            # 章节重排后
│   ├── course.json              # 含 origin, version
│   └── ...
└── ...

app.db                           # 数据库
└── courses 表
    └── id: uuid, code: python_basics_v1, ...
```

---

## 更新日志

- **2026-02-23**: 初始文档创建
- **2026-02-23**: 重新设计，移除批量导入，确立单一数据源原则，章节重排独立为可选流程
