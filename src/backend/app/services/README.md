# Services - 业务逻辑服务

服务层实现了 AILearn Hub 系统的核心业务逻辑，封装了数据访问和复杂的业务规则。

## 目录结构

```
app/services/
├── __init__.py
├── user_service.py                 # 用户管理服务
├── course_service.py               # 课程管理服务
├── question_set_service.py         # 题集管理服务
├── quiz_service.py                # 刷题模式服务
├── exam_service.py                # 考试模式服务
├── review_service.py              # 艾宾浩斯复习服务
├── user_settings_service.py       # 用户设置服务
└── user_course_progress_service.py # 用户课程进度服务（如有）
```

## 设计原则

### 1. 业务逻辑封装
- 服务层封装所有业务规则
- API 层只负责请求/响应处理
- 模型层只负责数据存储

### 2. 静态方法
- 所有服务方法使用 `@staticmethod`
- 不需要实例化服务类
- 便于测试和重用

### 3. 数据库会话管理
- 所有方法接收 `db: Session` 参数
- 不在服务内部创建/关闭数据库会话
- 由 API 层通过依赖注入提供

### 4. 事务管理
- 单个操作自动提交（`db.commit()`）
- 多个操作在一个事务中执行
- 异常时自动回滚

## 服务详解

### UserService (user_service.py)

用户管理服务，支持 Dev 模式和生产模式。

#### 核心方法

##### get_or_create_user()
获取或创建用户（Dev 模式）。

**特性：**
- 支持确定性用户 ID（基于昵称）
- 支持临时用户（免注册）
- 自动更新最后登录时间

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID（可选）
- `nickname`: 昵称（可选）

**返回：** `User` 对象

**示例：**
```python
# 创建新用户
user = UserService.get_or_create_user(db, nickname="张三")

# 获取现有用户
user = UserService.get_or_create_user(db, user_id="123")

# Dev 模式临时用户
user = UserService.get_or_create_user(db)
```

##### get_user_stats()
获取用户学习统计。

**统计指标：**
- `total_answered`: 总答题数
- `correct_count`: 正确数
- `accuracy`: 正确率
- `mastered_count`: 已掌握题目数
- `due_review_count`: 待复习题目数

**示例：**
```python
stats = UserService.get_user_stats(db, user_id="123")
# {
#   "total_answered": 100,
#   "correct_count": 80,
#   "accuracy": 80.0,
#   "mastered_count": 20,
#   "due_review_count": 5
# }
```

##### start_new_round()
开始新的一轮刷题（轮次管理核心逻辑）。

**轮次管理规则：**
- `current_round += 1`: 进入下一轮
- `total_rounds_completed += 1`: 记录完成轮次数
- 重置 `completed_in_current_round = False`: 让题目可以重新刷题

**示例：**
```python
progress = UserService.start_new_round(db, user_id="123", course_id="456")
# 返回更新后的 UserCourseProgress 对象
```

##### reset_user_data()
重置用户数据（Dev 模式）。

**删除内容：**
- 批次答题记录（`BatchAnswer`）
- 批次记录（`QuizBatch`）
- 学习记录（`UserLearningRecord`）

**示例：**
```python
success = UserService.reset_user_data(db, user_id="123")
```

### QuizService (quiz_service.py)

批次刷题服务，实现批次刷题和统一对答案。

#### 核心方法

##### start_batch()
开始一个新的刷题批次。

**特性：**
- 支持轮次跟踪
- 自动获取下一批题目
- 创建批次和答题记录

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `mode`: 模式（"practice" | "exam"）
- `batch_size`: 批次大小（默认 10）
- `course_id`: 课程 ID（必需）

**返回：** `QuizBatch` 对象

**示例：**
```python
batch = QuizService.start_batch(
    db,
    user_id="123",
    mode="practice",
    batch_size=10,
    course_id="456"
)
```

##### submit_batch_answer()
提交批次中的单题答案（批次进行中）。

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `batch_id`: 批次 ID
- `question_id`: 题目 ID
- `answer`: 用户答案

**返回：** `BatchAnswer` 对象

**示例：**
```python
answer = QuizService.submit_batch_answer(
    db,
    user_id="123",
    batch_id="789",
    question_id="111",
    answer="A"
)
```

##### finish_batch()
完成批次（统一对答案）。

**流程：**
1. 验证批次状态（必须为 "in_progress"）
2. 获取所有答题记录
3. 统一计算对错
4. 更新批次状态为 "completed"
5. 保存到学习记录（调用 `ReviewService.submit_answer`）

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `batch_id`: 批次 ID

**返回：**
```python
{
  "batch_id": "789",
  "total": 10,
  "correct": 8,
  "wrong": 2,
  "accuracy": 80.0
}
```

##### get_batch_questions()
获取批次中的题目和答题状态。

**特性：**
- 返回题目和答案
- 批次完成后显示正确答案和解析
- 显示题集来源信息

**返回：**
```python
[
  {
    "id": "111",
    "content": "题目内容",
    "question_type": "single_choice",
    "options": {"A": "...", "B": "..."},
    "correct_answer": "A",  # 仅批次完成后显示
    "explanation": "...",   # 仅批次完成后显示
    "user_answer": "A",
    "is_correct": True,     # 仅批次完成后显示
    "answered_at": "2024-01-01T00:00:00",
    "question_set_codes": ["基础题集"]
  }
]
```

### ReviewService (review_service.py)

艾宾浩斯复习调度服务，实现智能题目推荐。

#### 核心方法

##### submit_answer()
提交答案并更新学习记录（艾宾浩斯算法）。

**变更说明：**
- 创建历史答题记录（`UserAnswerHistory`），保留完整历史
- `UserLearningRecord` 只存储复习状态
- 错题推荐逻辑与 `is_correct` 解耦，只依赖 `review_stage`

**流程：**
1. 获取当前复习阶段
2. 创建历史答题记录（每次答题都创建新记录）
3. 使用艾宾浩斯算法计算下一阶段和复习时间
4. 更新学习记录的复习状态

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `question_id`: 题目 ID
- `answer`: 用户答案
- `is_correct`: 是否正确
- `batch_id`: 关联的批次 ID（可选）

**返回：** `UserLearningRecord` 对象

**示例：**
```python
record = ReviewService.submit_answer(
    db,
    user_id="123",
    question_id="111",
    answer="A",
    is_correct=True,
    batch_id="789"
)
```

##### get_next_question()
获取下一批复习题目（支持多轮模式）。

**优先级（修复版）：**
1. 艾宾浩斯复习阶段的题目（复习时间到了，当前轮次未刷过）
2. 当前轮次未刷过的其他题目（包括已掌握的）
3. 用户没刷过的题（新题）
4. 如果 `allow_new_round=True` 且没有可用题，开始新轮

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `course_id`: 课程 ID（可选）
- `batch_size`: 批次大小（默认 10）
- `allow_new_round`: 是否允许开始新轮（默认 True）

**返回：** `List[Question]` 题目列表

**示例：**
```python
questions = ReviewService.get_next_question(
    db,
    user_id="123",
    course_id="456",
    batch_size=10,
    allow_new_round=True
)
```

##### get_wrong_questions()
获取用户的错题列表。

**错题定义（修改版）：**
- 历史上曾经答错过（`UserAnswerHistory` 中存在 `is_correct == False` 的记录）
- 且当前未达到已掌握状态（`review_stage != 8`）

**变更说明：**
- 使用 `UserAnswerHistory` 表查询最近的做错时间
- 错题推荐逻辑与 `is_correct` 解耦，只依赖 `review_stage`

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `course_id`: 课程 ID（可选）
- `limit`: 限制数量（默认 100）

**返回：**
```python
{
  "questions": [Question, ...],  # 错题列表
  "wrong_times": {              # 最近的做错时间
    "111": datetime(...),
    "222": datetime(...)
  }
}
```

##### get_mastered_questions()
获取已掌握的题目。

**已掌握定义：**
- `review_stage == 8`（`EbbinghausScheduler.MAX_STAGE`）

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `course_id`: 课程 ID（可选）
- `limit`: 限制数量（默认 100）

**返回：** `List[Question]` 已掌握题目列表

### CourseService (course_service.py)

课程管理服务。

#### 核心方法

##### get_courses()
获取课程列表。

**参数：**
- `db`: 数据库会话
- `active_only`: 是否只返回启用的课程（默认 True）

**返回：** `List[Course]` 课程列表

**示例：**
```python
# 获取所有启用的课程
courses = CourseService.get_courses(db, active_only=True)

# 获取所有课程（包括停用的）
courses = CourseService.get_courses(db, active_only=False)
```

##### get_course_with_progress()
获取课程信息及其用户进度（含轮次信息）。

**返回信息：**
- 课程基本信息
- 用户进度（`current_round`, `total_rounds_completed`）

**参数：**
- `db`: 数据库会话
- `course_id`: 课程 ID
- `user_id`: 用户 ID（可选）

**返回：**
```python
{
  "id": "456",
  "code": "ai_cert_exam",
  "title": "AI 认证考试",
  "description": "...",
  "course_type": "exam",
  "cover_image": "...",
  "default_exam_config": {...},
  "is_active": True,
  "sort_order": 1,
  "created_at": "2024-01-01T00:00:00",
  "current_round": 2,           # 用户进度
  "total_rounds_completed": 1    # 用户进度
}
```

### ExamService (exam_service.py)

考试模式服务，实现固定题集和动态抽取考试。

#### 核心方法

##### start_exam()
开始一次考试。

**支持两种模式：**
1. **extraction**: 动态抽取题目（按题型数量）
2. **fixed_set**: 使用固定题集

**配置优先级：**
请求参数 > 用户设置 > 课程默认 > 硬编码

**轮次管理逻辑（修复版）：**
- 在开始考试前，通过获取 1 个题来触发轮次检查
- 如果题库中所有题目都已刷完（无可用题），会自动开启新轮

**参数：**
- `db`: 数据库会话
- `user_id`: 用户 ID
- `course_id`: 课程 ID（必需）
- `exam_mode`: 考试模式（"extraction" | "fixed_set"）
- `question_type_config`: 题型配置（如 `{"single_choice": 30}`）
- `difficulty_range`: 难度范围 `[1,5]`
- `question_set_code`: 固定题集代码（fixed_set 模式必需）

**返回：** `QuizBatch` 考试批次对象

**示例：**
```python
# 动态抽取模式
batch = ExamService.start_exam(
    db,
    user_id="123",
    course_id="456",
    exam_mode="extraction",
    question_type_config={
      "single_choice": 30,
      "multiple_choice": 10,
      "true_false": 10
    },
    difficulty_range=[1, 5]
)

# 固定题集模式
batch = ExamService.start_exam(
    db,
    user_id="123",
    course_id="456",
    exam_mode="fixed_set",
    question_set_code="set1"
)
```

## 轮次管理与艾宾浩斯复习的解耦

### 核心设计

轮次管理与艾宾浩斯复习算法是两个独立的系统：

#### 轮次管理（轮次系统）
- 目的：跟踪用户在每个课程上的刷题轮次
- 字段：`UserCourseProgress.current_round`, `total_rounds_completed`
- 触发：当用户完成课程所有题目后，自动进入下一轮
- 标志：`UserLearningRecord.completed_in_current_round`
- 影响：在新轮次中，所有题目都可以重新刷题

#### 艾宾浩斯复习（复习系统）
- 目的：基于遗忘曲线智能推荐复习题目
- 字段：`UserLearningRecord.review_stage`, `next_review_time`
- 触发：每次答题后，根据对错更新复习阶段和下次复习时间
- 标志：`review_stage`（0-7: 复习中，8: 已掌握）
- 影响：优先推荐需要复习的题目

### 交互关系

**题目推荐优先级（ReviewService.get_next_question）：**

1. **优先级 1：艾宾浩斯复习题目**
   - 条件：`review_stage` 在 1-7 之间
   - 条件：`next_review_time <= now`（复习时间到了）
   - 条件：与轮次无关

2. **优先级 2：当前轮次未刷过的题目**
   - 条件：`completed_in_current_round == False`
   - 条件：`review_stage` 任意（包括已掌握的）
   - 排除：已选中的复习题

3. **优先级 3：新题**
   - 条件：没有任何学习记录
   - 条件：或 `review_stage == 0` 且 `next_review_time == None`

4. **优先级 4：开始新轮**
   - 条件：`allow_new_round == True`
   - 条件：没有可用题目（所有题目都已刷完）
   - 操作：调用 `UserService.start_new_round()`

### 数据一致性

| 场景 | `review_stage` | `next_review_time` | `completed_in_current_round` | 解释 |
|------|---------------|-------------------|----------------------------|------|
| 新题 | 0 | None | False | 未刷过，需要初次学习 |
| 答对 | 1 | 30分钟后 | True | 答对进入第1阶段 |
| 复习到期 | 1 | ≤ now | False | 需要复习 |
| 答错 | 1 | 30分钟后 | True | 回到第1阶段 |
| 已掌握 | 8 | None | True | 已掌握，无需复习 |
| 新轮开始 | 保持 | 保持 | False | 重置轮次标记 |

## 注意事项

### 1. 时间处理
- 所有时间使用 UTC 时区
- 使用 `datetime.utcnow()` 获取当前时间
- 时区转换使用 `datetime.now(timezone.utc)`

### 2. UUID 生成
- 所有 ID 使用 `str(uuid.uuid4())` 生成
- 确定性 ID 使用 SHA256 哈希

### 3. 事务管理
- 单个操作自动提交
- 多个操作在一个事务中
- 异常时自动回滚

### 4. 数据验证
- 所有输入参数需要验证
- 使用 `ValueError` 抛出业务异常
- API 层转换为 HTTP 状态码

### 5. 软删除
- 使用 `is_deleted` 标记删除
- 查询时过滤已删除记录
- 不物理删除数据

## 扩展指南

### 添加新服务

1. 创建服务文件：

```python
# app/services/new_service.py
from sqlalchemy.orm import Session

class NewService:
    """新服务"""

    @staticmethod
    def do_something(db: Session, param: str):
        """执行某些操作"""
        # 业务逻辑
        pass
```

2. 在 API 层使用：

```python
from app.services import NewService

@router.post("/something")
async def do_something(
    param: str,
    db: Session = Depends(get_db)
):
    result = NewService.do_something(db, param)
    return result
```

### 添加新方法

在现有服务中添加新方法：

1. 遵循命名约定（动词开头）
2. 使用类型注解
3. 添加详细文档字符串
4. 包含参数说明和返回值说明

## 相关文档

- [数据模型](../models/README.md)
- [核心模块](../core/README.md)
- [API 路由](../api/README.md)
