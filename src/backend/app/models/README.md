# Models - 数据模型

数据模型层定义了 AILearn Hub 系统的数据库结构，使用 SQLAlchemy ORM 实现。

## 目录结构

```
app/models/
├── __init__.py                    # 模型导入
├── base.py                       # Base 类定义
├── user.py                       # 用户模型
├── course.py                     # 课程模型
├── question.py                   # 题目模型
├── question_set.py               # 题集模型
├── batch.py                      # 批次模型
├── record.py                     # 学习记录模型
├── answer_history.py            # 答题历史模型
├── user_course_progress.py      # 用户课程进度模型
└── user_settings.py             # 用户设置模型
```

## Base 类 (base.py)

### Base

所有数据模型的基类，由 SQLAlchemy 的 `declarative_base()` 创建。

```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

**用途：**
- 所有模型继承自 `Base`
- 提供统一的模型元数据
- 支持表创建和迁移

## 用户模型 (user.py)

### User

用户表，支持 Dev 模式和生产模式。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 用户ID（UUID） | PRIMARY KEY, INDEX |
| `username` | String(50) | 用户名 | UNIQUE, NOT NULL, INDEX |
| `email` | String(100) | 邮箱 | UNIQUE, NOT NULL |
| `password_hash` | String(255) | 密码哈希 | NOT NULL |
| `nickname` | String(100) | 昵称 | NULLABLE |
| `is_temp_user` | Boolean | 是否临时用户（Dev模式） | DEFAULT: False |
| `total_study_time` | Integer | 总学习时间（秒） | DEFAULT: 0 |
| `user_level` | String(20) | 用户等级 | NULLABLE |
| `created_at` | DateTime | 创建时间 | DEFAULT: NOW |
| `last_login` | DateTime | 最后登录时间 | NULLABLE |
| `is_deleted` | Boolean | 是否已删除 | DEFAULT: False |

#### 关系

- `batches`: 与 `QuizBatch` 一对多关系
  - 一个用户可以有多个刷题批次

#### 示例

```python
# 创建用户
user = User(
    id=str(uuid.uuid4()),
    username="user123",
    email="user@example.com",
    password_hash="hashed_password",
    nickname="Nick"
)

# 查询用户
user = db.query(User).filter(User.username == "user123").first()

# Dev 模式临时用户
temp_user = User(
    id=str(uuid.uuid4()),
    username=f"temp_{uuid.uuid4().hex[:8]}",
    email=f"temp_{uuid.uuid4().hex[:8]}@temp.com",
    password_hash="temp",
    is_temp_user=True
)
```

## 课程模型 (course.py)

### Course

课程表，存储课程信息和默认考试配置。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 课程ID（UUID） | PRIMARY KEY, INDEX |
| `code` | String(50) | 课程代码 | UNIQUE, NOT NULL, INDEX |
| `title` | String(200) | 课程标题 | NOT NULL |
| `description` | Text | 课程描述 | NULLABLE |
| `course_type` | String(20) | 课程类型 | NOT NULL, INDEX |
| `cover_image` | String(500) | 封面图URL | NULLABLE |
| `default_exam_config` | JSON | 默认考试配置 | NULLABLE |
| `is_active` | Boolean | 是否启用 | DEFAULT: True |
| `sort_order` | Integer | 排序 | DEFAULT: 0 |
| `created_at` | DateTime | 创建时间 | DEFAULT: NOW |
| `is_deleted` | Boolean | 是否已删除 | DEFAULT: False |

#### default_exam_config 结构

```json
{
  "question_type_config": {
    "single_choice": 30,
    "multiple_choice": 10,
    "true_false": 10
  },
  "difficulty_range": [1, 5]
}
```

#### 关系

- `questions`: 与 `Question` 一对多关系
  - 一个课程包含多个题目
- `question_sets`: 与 `QuestionSet` 一对多关系
  - 一个课程包含多个题集

#### 示例

```python
# 创建课程
course = Course(
    id=str(uuid.uuid4()),
    code="ai_cert_exam",
    title="AI 认证考试",
    description="人工智能认证考试题库",
    course_type="exam",
    default_exam_config={
        "question_type_config": {
            "single_choice": 30,
            "multiple_choice": 10,
            "true_false": 10
        },
        "difficulty_range": [1, 5]
    }
)
```

## 题目模型 (question.py)

### Question

题目表，存储题目内容和元数据。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 题目ID（UUID） | PRIMARY KEY, INDEX |
| `course_id` | String(36) | 所属课程ID | FOREIGN KEY, NOT NULL, INDEX |
| `question_type` | String(20) | 题目类型 | NOT NULL, INDEX |
| `content` | Text | 题目内容 | NOT NULL |
| `options` | JSON | 选项（选择题） | NULLABLE |
| `correct_answer` | String(10) | 正确答案 | NOT NULL, INDEX |
| `explanation` | Text | 解析 | NULLABLE |
| `knowledge_points` | JSON | 知识点 | NULLABLE |
| `difficulty` | Integer | 难度（1-5） | DEFAULT: 2 |
| `question_set_ids` | JSON | 所属题集ID列表 | NULLABLE |
| `is_controversial` | Boolean | 是否有争议 | DEFAULT: False |
| `extra_data` | JSON | 额外数据 | DEFAULT: {} |
| `vector_id` | String(100) | 向量ID（用于搜索） | NULLABLE |
| `created_at` | DateTime | 创建时间 | DEFAULT: NOW |
| `is_deleted` | Boolean | 是否已删除 | DEFAULT: False |

#### question_type 值

- `single_choice`: 单选题
- `multiple_choice`: 多选题
- `true_false`: 判断题

#### options 结构（单选/多选题）

```json
{
  "A": "选项A",
  "B": "选项B",
  "C": "选项C",
  "D": "选项D"
}
```

#### correct_answer 格式

- 单选题：`"A"`, `"B"`, `"C"`, `"D"`
- 多选题：`"AB"`, `"ACD"`, `"BC"`
- 判断题：`"T"` (True), `"F"` (False)

#### 关系

- `course`: 与 `Course` 多对一关系
  - 一个题目属于一个课程
- `records`: 与 `UserLearningRecord` 一对多关系
  - 一个题目可以有多个学习记录

#### 示例

```python
# 单选题
question = Question(
    id=str(uuid.uuid4()),
    course_id=course.id,
    question_type="single_choice",
    content="以下哪个是机器学习算法？",
    options={"A": "线性回归", "B": "HTML", "C": "CSS", "D": "JavaScript"},
    correct_answer="A",
    explanation="线性回归是一种监督学习算法",
    knowledge_points=["监督学习", "线性模型"],
    difficulty=2
)

# 判断题
question = Question(
    id=str(uuid.uuid4()),
    course_id=course.id,
    question_type="true_false",
    content="深度学习是机器学习的子集",
    correct_answer="T",
    explanation="深度学习是机器学习的一个分支",
    knowledge_points=["深度学习", "机器学习"],
    difficulty=1
)
```

## 题集模型 (question_set.py)

### QuestionSet

题集表，用于固定题集管理。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 题集ID（UUID） | PRIMARY KEY, INDEX |
| `course_id` | String(36) | 所属课程ID | FOREIGN KEY, NOT NULL, INDEX |
| `code` | String(50) | 题集代码 | UNIQUE, NOT NULL, INDEX |
| `name` | String(200) | 题集名称 | NOT NULL |
| `description` | Text | 题集描述 | NULLABLE |
| `total_questions` | Integer | 题目总数 | DEFAULT: 0 |
| `is_active` | Boolean | 是否启用 | DEFAULT: True |
| `created_at` | DateTime | 创建时间 | DEFAULT: NOW |
| `is_deleted` | Boolean | 是否已删除 | DEFAULT: False |

#### 关系

- `course`: 与 `Course` 多对一关系
  - 一个题集属于一个课程

#### 示例

```python
question_set = QuestionSet(
    id=str(uuid.uuid4()),
    course_id=course.id,
    code="set1",
    name="基础题集",
    description="机器学习基础知识",
    total_questions=100
)
```

## 批次模型 (batch.py)

### QuizBatch

刷题/考试批次表，记录每次学习会话。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 批次ID（UUID） | PRIMARY KEY |
| `user_id` | String(36) | 用户ID | FOREIGN KEY, NOT NULL, INDEX |
| `batch_size` | Integer | 批次大小 | DEFAULT: 10 |
| `mode` | String(20) | 模式 | DEFAULT: "practice" |
| `round_number` | Integer | 轮次编号 | DEFAULT: 1 |
| `started_at` | DateTime | 开始时间 | DEFAULT: NOW, INDEX |
| `completed_at` | DateTime | 完成时间 | NULLABLE |
| `status` | String(20) | 状态 | DEFAULT: "in_progress" |
| `is_deleted` | Boolean | 是否已删除 | DEFAULT: False |

#### mode 值

- `practice`: 刷题模式
- `exam`: 考试模式

#### status 值

- `in_progress`: 进行中
- `completed`: 已完成

#### 关系

- `user`: 与 `User` 多对一关系
  - 一个批次属于一个用户
- `answers`: 与 `BatchAnswer` 一对多关系
  - 一个批次包含多个答题记录

### BatchAnswer

批次答题记录表，记录批次内每道题的答案。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 答题记录ID（UUID） | PRIMARY KEY |
| `batch_id` | String(36) | 批次ID | FOREIGN KEY, NOT NULL, INDEX |
| `question_id` | String(36) | 题目ID | FOREIGN KEY, NOT NULL, INDEX |
| `user_answer` | String(10) | 用户答案 | NULLABLE |
| `is_correct` | Boolean | 是否正确 | NULLABLE |
| `answered_at` | DateTime | 答题时间 | DEFAULT: NOW |

#### 关系

- `batch`: 与 `QuizBatch` 多对一关系
  - 一个答题记录属于一个批次
- `question`: 与 `Question` 多对一关系
  - 一个答题记录对应一个题目

#### 示例

```python
# 创建批次
batch = QuizBatch(
    id=str(uuid.uuid4()),
    user_id=user.id,
    batch_size=10,
    mode="practice",
    round_number=1
)

# 记录答案
answer = BatchAnswer(
    id=str(uuid.uuid4()),
    batch_id=batch.id,
    question_id=question.id,
    user_answer="A",
    is_correct=True
)
```

## 学习记录模型 (record.py)

### UserLearningRecord

用户学习记录表，记录每个题目的复习状态（艾宾浩斯算法）。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 记录ID（UUID） | PRIMARY KEY |
| `user_id` | String(36) | 用户ID | FOREIGN KEY, NOT NULL, INDEX |
| `question_id` | String(36) | 题目ID | FOREIGN KEY, NOT NULL, INDEX |
| `review_stage` | Integer | 复习阶段（0-8） | DEFAULT: 0, INDEX |
| `next_review_time` | DateTime | 下次复习时间 | NULLABLE, INDEX |
| `completed_in_current_round` | Boolean | 当前轮次是否完成 | DEFAULT: False, INDEX |

#### review_stage 值

- `0`: 新题
- `1-7`: 复习阶段（1-7）
- `8`: 已掌握（MASTERED）

#### 艾宾浩斯算法

详见：[core/README.md](../core/README.md)

#### 关系

- `question`: 与 `Question` 多对一关系
  - 一个学习记录对应一个题目

#### 示例

```python
# 新题记录
record = UserLearningRecord(
    id=str(uuid.uuid4()),
    user_id=user.id,
    question_id=question.id,
    review_stage=0,
    next_review_time=None,
    completed_in_current_round=False
)

# 答对后更新
record.review_stage = 1
record.next_review_time = datetime.utcnow() + timedelta(minutes=30)

# 已掌握
record.review_stage = 8
record.next_review_time = None
```

## 答题历史模型 (answer_history.py)

### AnswerHistory

答题历史表，记录所有答题历史（用于统计）。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 记录ID（UUID） | PRIMARY KEY |
| `user_id` | String(36) | 用户ID | FOREIGN KEY, NOT NULL, INDEX |
| `question_id` | String(36) | 题目ID | FOREIGN KEY, NOT NULL, INDEX |
| `user_answer` | String(10) | 用户答案 | NOT NULL |
| `is_correct` | Boolean | 是否正确 | NOT NULL |
| `answered_at` | DateTime | 答题时间 | DEFAULT: NOW, INDEX |

#### 关系

- `user`: 与 `User` 多对一关系
- `question`: 与 `Question` 多对一关系

## 用户课程进度模型 (user_course_progress.py)

### UserCourseProgress

用户课程进度表，跟踪用户在每个课程的学习进度。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 进度ID（UUID） | PRIMARY KEY |
| `user_id` | String(36) | 用户ID | FOREIGN KEY, NOT NULL, INDEX |
| `course_id` | String(36) | 课程ID | FOREIGN KEY, NOT NULL, INDEX |
| `current_round` | Integer | 当前轮次 | DEFAULT: 1 |
| `total_rounds_completed` | Integer | 完成轮次数 | DEFAULT: 0 |
| `last_studied_at` | DateTime | 最后学习时间 | NULLABLE |

#### 关系

- `user`: 与 `User` 多对一关系
- `course`: 与 `Course` 多对一关系

#### 示例

```python
progress = UserCourseProgress(
    id=str(uuid.uuid4()),
    user_id=user.id,
    course_id=course.id,
    current_round=1,
    total_rounds_completed=0
)
```

## 用户设置模型 (user_settings.py)

### UserSettings

用户设置表，存储用户个性化设置。

#### 字段

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| `id` | String(36) | 设置ID（UUID） | PRIMARY KEY |
| `user_id` | String(36) | 用户ID | FOREIGN KEY, NOT NULL, INDEX |
| `batch_size` | Integer | 批次大小 | DEFAULT: 10 |
| `auto_next` | Boolean | 自动下一题 | DEFAULT: False |
| `show_explanation` | Boolean | 显示解析 | DEFAULT: True |

#### 关系

- `user`: 与 `User` 多对一关系（一对一）

## 数据库关系图

```
User (用户)
  ├── QuizBatch (刷题批次)
  │     └── BatchAnswer (批次答题记录)
  ├── UserLearningRecord (学习记录)
  ├── AnswerHistory (答题历史)
  ├── UserCourseProgress (课程进度)
  └── UserSettings (用户设置)

Course (课程)
  ├── Question (题目)
  │     ├── UserLearningRecord (学习记录)
  │     ├── BatchAnswer (答题记录)
  │     └── AnswerHistory (答题历史)
  └── QuestionSet (题集)
        └── Question (题目关联)
```

## 使用示例

### 创建表

```python
from app.core.database import engine
from app.models.base import Base

# 创建所有表
Base.metadata.create_all(bind=engine)
```

### 查询示例

```python
from sqlalchemy.orm import Session
from app.models import User, Question, QuizBatch, UserLearningRecord

# 查询用户
user = db.query(User).filter(User.id == user_id).first()

# 查询课程题目
questions = db.query(Question).filter(Question.course_id == course_id).all()

# 查询用户的刷题批次
batches = db.query(QuizBatch).filter(
    QuizBatch.user_id == user_id,
    QuizBatch.status == "completed"
).order_by(QuizBatch.started_at.desc()).all()

# 查询待复习题目
from datetime import datetime
due_records = db.query(UserLearningRecord).filter(
    UserLearningRecord.user_id == user_id,
    UserLearningRecord.next_review_time <= datetime.utcnow(),
    UserLearningRecord.review_stage < 8
).all()
```

## 注意事项

1. **ID 格式**
   - 所有主键使用 UUID 字符串格式
   - 使用 `str(uuid.uuid4())` 生成

2. **时间处理**
   - 所有时间使用 UTC 时区
   - 使用 `datetime.utcnow()` 获取当前时间

3. **JSON 字段**
   - SQLAlchemy 将 JSON 字段存储为字符串
   - Python 操作时自动转换为 dict/list

4. **软删除**
   - 使用 `is_deleted` 标记删除
   - 查询时过滤已删除记录

5. **关系查询**
   - 使用 `relationship` 定义的属性进行关联查询
   - 注意使用 `back_populates` 保持双向关系

## 相关文档

- [核心模块](../core/README.md)
- [业务服务](../services/README.md)
- [API 路由](../api/README.md)

## 扩展指南

### 添加新模型

1. 创建新的模型文件：

```python
# app/models/new_model.py
from sqlalchemy import Column, String
from app.models.base import Base

class NewModel(Base):
    """新模型"""
    __tablename__ = "new_models"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
```

2. 在 `__init__.py` 中导入：

```python
from .new_model import NewModel
```

3. 创建表：

```python
from app.models.base import Base
Base.metadata.create_all(bind=engine)
```
