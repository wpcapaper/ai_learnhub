# 课程选择功能 - 修改意图与计划

## 文档信息
- **创建日期**: 2026-01-20
- **作者**: Sisyphus AI Agent
- **目标分支**: feature/course-selection
- **关联任务**: 考前快速开发刷题系统阶段
- **当前版本**: v4.0 - 激进方案 + UserSettings + 错题本 + 艾宾浩斯调整
  - v1.0: 初始计划文档
  - v2.0: 添加QuestionSet模型和双模式考试系统
  - v3.0: 激进设计 + UserSettings（Phase 1数据模型，Phase 2个性化）
  - v4.0: 错题本模块 + 艾宾浩斯算法调整（错题进入曲线，答对不进入）

## 设计原则
- **0-1阶段激进简化**：无历史数据，采用简洁数据模型
- **渐进式扩展**：Phase 1数据模型支持，Phase 2前端界面
- **配置优先级**：用户设置 > 课程默认 > 硬编码
- **强制规范**：统一使用code标识，支持多文件导入
- **错题优先**：错题必须进入艾宾浩斯记忆曲线，答对的题不进入

---

## 一、现状评估

### 1.1 当前项目架构分析

#### 技术栈
- **前端**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **后端**: FastAPI + SQLAlchemy + SQLite (Dev模式) / PostgreSQL (生产)
- **状态管理**: React Context API
- **架构模式**: 前后端分离，RESTful API

#### 当前页面结构
```
src/frontend/app/
├── page.tsx              # 首页：用户登录/选择模式
├── quiz/page.tsx          # 批次刷题页面（二级界面）
├── exam/page.tsx          # 考试模式页面（二级界面）
├── stats/page.tsx         # 学习统计页面
├── context.tsx            # 全局状态管理
└── layout.tsx            # 根布局
```

#### 当前用户流程
```
1. 用户访问首页 → 输入昵称 → 创建用户
2. 首页显示三个模式卡片：
   - 刷题模式 (/quiz)
   - 考试模式 (/exam)
   - 学习统计 (/stats)
3. 点击"刷题模式"或"考试模式" → 直接进入答题界面（无课程选择）
```

### 1.2 数据模型现状

#### Question模型（题目表）
```python
class Question(Base):
    id = Column(String(36), primary_key=True)
    course_type = Column(String(20), default="exam")  # exam | learning
    question_type = Column(String(20))                 # single_choice | multiple_choice | true_false
    content = Column(Text)
    options = Column(JSON)
    correct_answer = Column(String(10))
    explanation = Column(Text)
    knowledge_points = Column(JSON)
    difficulty = Column(Integer)
    # ... 其他字段
```

**关键发现**:
- ✅ 支持course_type字段（exam | learning）
- ❌ **没有独立的Course实体**
- ❌ **没有course_id外键**：题目无法关联到具体课程，只能按course_type分组
- ❌ course_type作为题目属性而非课程关系，导致同类课程（如多个exam类型课程）的题目混在一起

**核心问题**：
- course_type只能区分课程类型，无法区分具体课程实例
- 例如："AI认证考试"和"机器学习基础"都是exam类型，但题目应该分开管理

#### 现有服务层
- `QuizService`: 批次刷题逻辑
- `ExamService`: 考试模式逻辑（支持course_type参数）
- `ReviewService`: 复习调度（艾宾浩斯算法）

### 1.3 现有API分析

#### 刷题相关API
```
POST /api/quiz/start
- 参数: mode, batch_size, course_type
- 硬编码: course_type="exam"
- 问题: 没有从前端接收course_id

POST /api/exam/start
- 参数: total_questions, difficulty_range, course_type
- 硬编码: course_type="exam"
- 问题: 没有从前端接收course_id
```

**关键发现**:
- ✅ API已经支持course_type参数
- ❌ 没有课程管理API（获取课程列表、课程详情等）
- ❌ 没有course_id参数传递

### 1.4 核心问题总结

| 问题 | 严重程度 | 影响 |
|------|---------|------|
| **缺失课程选择界面** | P0 | 用户无法选择要学习的课程 |
| **无Course实体** | P0 | 无法管理课程元数据（标题、描述等） |
| **Question缺少course_id** | P0 | 题目无法关联到具体课程，只能按course_type分组 |
| **前端流程不完整** | P0 | 直接进入答题，跳过了课程选择这一级 |
| **API缺少课程接口** | P0 | 无法获取课程列表 |
| **导入脚本不支持课程** | P0 | 导入时无法指定课程，无法多文件导入到同一课程 |

---

## 二、修改意图

### 2.1 业务目标

在考前快速开发刷题系统阶段，虽然重点是刷题功能，但必须支持基本的课程选择能力，以支撑：

1. **多课程支持**: 未来可能有多个刷题类课程（如：AI认证考试、机器学习基础等）
2. **课程区分**: 不同课程有不同的题目集和刷题策略
3. **扩展性**: 为阶段2的完整学习系统预留课程管理能力

### 2.2 设计原则

1. **最小化改动**: 在现有架构基础上增量添加，不重构核心逻辑
2. **向后兼容**: 现有exam类型课程保持可用
3. **快速开发**: 针对刷题场景简化课程管理，不过度设计
4. **可扩展**: 为未来完整课程管理预留扩展点

### 2.3 核心需求

#### P0功能（必须实现）
- [x] 创建Course数据模型
- [x] 创建QuestionSet数据模型（固定题集+动态配置）
- [x] 添加课程管理API（列表、详情）
- [x] 添加题集管理API（列表、详情、题目）
- [x] 修改Question模型，添加course_id和question_set_ids
- [x] 创建课程选择页面（/courses）
- [x] 修改首页链接，跳转到课程选择页
- [x] 修改刷题/考试页面，接收course_id参数
- [x] 考试模式支持两种方式：
  - 从题库按题型数量抽取（如单选30、多选10、判断10）
  - 使用固定题集（预导入的固定题目集合）
- [x] 题型数量验证（不能高于题库上限）
- [x] 导入脚本支持：
  - 指定课程（--course-code/--course-id）
  - 创建固定题集（--create-question-set）
  - 多文件导入到同一课程/题集
- [x] 刷题模式显示题目来源（"考试题"及题集名称）

#### P1功能（可选，如果时间允许）
- [ ] 错题本页面（专门管理错题）
- [ ] 课程封面图片
- [ ] 课程描述和元数据
- [ ] 课程进度统计

#### 明确不做（阶段1）
- ❌ 完整的课程CRUD管理界面（后台管理）
- ❌ 课程章节管理（阶段2功能）
- ❌ 课程内容导入系统（Markdown教程等，阶段2功能）
- ❌ 复杂的课程权限管理
- ❌ 考试题库的高级配置（难度自适应、知识点覆盖等）
- ❌ 固定题集的编辑和管理界面（通过导入脚本创建即可）

### 2.4 错题记录与艾宾浩斯算法调整

**现状问题**：
- 当前ReviewService.submit_answer()中，无论答对还是答错，都会调用EbbinghausScheduler.calculate_next_review()
- 这意味着答对的题目也会进入艾宾浩斯记忆曲线
- 缺少专门的错题管理模块

**调整目标**：
1. **错题记录模块**：专门管理用户的错题
2. **艾宾浩斯算法调整**：
   - ✅ 错题必须进入艾宾浩斯记忆曲线
   - ❌ 答对的题不进入艾宾浩斯记忆曲线（仅在错题状态下才计算复习时间）
   - ✅ 曲线时间按最近一次做错的时间计算

**调整后的逻辑**：

```python
def submit_answer(
    db: Session,
    user_id: str,
    question_id: str,
    answer: str,
    is_correct: bool
) -> UserLearningRecord:
    """
    提交答案并更新复习进度（调整版）

    调整后的逻辑：
    - 答错：进入艾宾浩斯记忆曲线，计算next_review_time
    - 答对：
      * 如果当前是错题状态（review_stage > 0）：保持复习状态
      * 如果当前是未刷过/答对状态：不设置next_review_time（不进入曲线）
    """
    now = datetime.utcnow()

    # 查找现有记录
    record = db.query(UserLearningRecord).filter(
        UserLearningRecord.user_id == user_id,
        UserLearningRecord.question_id == question_id
    ).first()

    if record:
        # 更新现有记录
        if not is_correct:
            # 答错：进入/保持在艾宾浩斯记忆曲线
            current_stage = record.review_stage or 0
            next_stage, next_review_time = EbbinghausScheduler.calculate_next_review(
                current_stage, is_correct=False
            )

            record.is_correct = is_correct
            record.answer = answer
            record.answered_at = now
            record.review_stage = next_stage
            record.next_review_time = next_review_time
        else:
            # 答对：不进入艾宾浩斯记忆曲线
            record.is_correct = is_correct
            record.answer = answer
            record.answered_at = now
            # ✅ 关键：不更新review_stage和next_review_time
            # 如果当前已经在复习曲线中（review_stage > 0），保持不变
            # 如果当前不在复习曲线中（review_stage = 0），不进入曲线
    else:
        # 创建新记录
        if not is_correct:
            # 答错：进入艾宾浩斯记忆曲线
            next_stage, next_review_time = EbbinghausScheduler.calculate_next_review(0, False)

            record = UserLearningRecord(
                id=f"{user_id}_{question_id}",
                user_id=user_id,
                question_id=question_id,
                is_correct=is_correct,
                answer=answer,
                answered_at=now,
                review_stage=next_stage,
                next_review_time=next_review_time
            )
        else:
            # 答对：不进入艾宾浩斯记忆曲线
            record = UserLearningRecord(
                id=f"{user_id}_{question_id}",
                user_id=user_id,
                question_id=question_id,
                is_correct=is_correct,
                answer=answer,
                answered_at=now,
                review_stage=0,  # 新题
                next_review_time=None  # ✅ 不设置复习时间
            )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record
```

**错题查询逻辑**：
```python
def get_wrong_questions(
    db: Session,
    user_id: str,
    course_id: str = None
) -> List[Question]:
    """
    获取用户的错题列表
    
    定义：
    - 错题：最近一次答题为错的题目（is_correct = False）
    - 如果答对后又答错，以最后一次为准
    
    Returns:
        List[Question]: 错题列表
    """
    # 子查询：获取每个题目的最新记录
    subquery = (
        db.query(
            UserLearningRecord.question_id,
            func.max(UserLearningRecord.answered_at).label('last_answered_at')
        )
        .filter(UserLearningRecord.user_id == user_id)
        .group_by(UserLearningRecord.question_id)
        .subquery()
    )

    # 查询最新记录中is_correct=False的题目
    query = (
        db.query(Question)
        .join(UserLearningRecord, and_(
            UserLearningRecord.question_id == Question.id,
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.is_correct == False,
            UserLearningRecord.answered_at == subquery.c.last_answered_at
        ))
        .filter(Question.is_deleted == False)
    )

    if course_id:
        query = query.filter(Question.course_id == course_id)

    wrong_questions = query.all()
    return wrong_questions
```

**艾宾浩斯复习查询逻辑（调整版）**：
```python
def get_next_question(
    db: Session,
    user_id: str,
    course_id: str = None,  # ✅ 改为course_id
    batch_size: int = 10
) -> List[Question]:
    """
    获取下一批复习题目（调整版）

    优先级（调整后）：
    1. 需要复习的错题（review_stage > 0 且 next_review_time <= now）
    2. 用户没刷过的题（review_stage = 0 且 next_review_time = None）
    
    注意：已答对的题（is_correct = True 且 review_stage = 0）不在复习队列中
    """
    now = datetime.utcnow()

    # 1. 优先：需要复习的错题
    wrong_due_query = (
        db.query(Question)
        .join(UserLearningRecord, UserLearningRecord.question_id == Question.id)
        .filter(
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.is_correct == False,  # 错题
            UserLearningRecord.next_review_time <= now,  # 到期复习
            UserLearningRecord.review_stage > 0,  # 在复习曲线中
            Question.is_deleted == False
        )
    )

    if course_id:
        wrong_due_query = wrong_due_query.filter(Question.course_id == course_id)

    wrong_due_questions = wrong_due_query.limit(batch_size).all()

    if len(wrong_due_questions) >= batch_size:
        return wrong_due_questions

    # 2. 次优先：用户没刷过的题（review_stage = 0 且 next_review_time = None）
    remaining_slots = batch_size - len(wrong_due_questions)

    new_questions_query = (
        db.query(Question)
        .outerjoin(UserLearningRecord, and_(
            UserLearningRecord.question_id == Question.id,
            UserLearningRecord.user_id == user_id
        ))
        .filter(
            or_(
                UserLearningRecord.id == None,  # 从未刷过
                and_(
                    UserLearningRecord.review_stage == 0,
                    UserLearningRecord.next_review_time.is_(None)  # 答对的题，不在曲线中
                )
            ),
            Question.is_deleted == False
        )
    )

    if course_id:
        new_questions_query = new_questions_query.filter(Question.course_id == course_id)

    new_questions = new_questions_query.limit(remaining_slots).all()

    result = wrong_due_questions + new_questions
    return result[:batch_size]
```

**错题本API设计**：
```python
# 路由: /api/mistakes/
router = APIRouter(prefix="/mistakes", tags=["错题管理"])

# 1. 获取错题列表
GET /api/mistakes/
Query: 
  - user_id: string (必需）
  - course_id: string (可选）
Response: List[Question]

# 2. 获取错题统计
GET /api/mistakes/stats
Query: user_id
Response: {
  "total_wrong": int,
  "wrong_by_course": {
    "course-1": 10,
    "course-2": 5
  },
  "wrong_by_type": {
    "single_choice": 8,
    "multiple_choice": 5,
    "true_false": 2
  }
}

# 3. 重做错题（批次）
POST /api/mistakes/retry
Body: {
  "user_id": "xxx",
  "course_id": "yyy",  # 可选
  "batch_size": 10
}
Response: {
  "batch_id": "zzz",
  "questions": [...]
}
```

**前端错题本页面**（Phase 1: 简化版）：
- 路径：`/mistakes`
- 功能：
  - 显示错题列表
  - 按课程筛选
  - 点击题目查看详情和解析
  - "重做"按钮：将错题加入当前批次
- **Phase 1简化**：
  - 直接使用现有的Quiz API重做错题
  - 不需要专门的错题重做批次逻辑

---

## 三、技术方案

### 3.1 数据库设计

#### 新增Course模型（激进版 - 0-1阶段）

```python
class Course(Base):
    """课程模型（激进版 - 含默认配置）"""
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 课程代码
    title = Column(String(200), nullable=False)                          # 课程标题
    description = Column(Text)                                            # 课程描述
    course_type = Column(String(20), nullable=False, index=True)         # exam | learning
    cover_image = Column(String(500), nullable=True)                    # 封面图URL

    # ✅ 新增：默认考试配置（系统级）
    default_exam_config = Column(JSON, nullable=True, default={
        "question_type_config": {
            "single_choice": 30,
            "multiple_choice": 10,
            "true_false": 10
        },
        "difficulty_range": [1, 5]
    })

    is_active = Column(Boolean, default=True)                            # 是否启用
    sort_order = Column(Integer, default=0)                             # 排序
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # 关系
    questions = relationship("Question", back_populates="course")
    question_sets = relationship("QuestionSet", backref="course")

    def __repr__(self):
        return f"<Course(id='{self.id}' code='{self.code}' title='{self.title}')>"
```

**默认配置示例**：
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

**course_code说明**：
- 课程的可读唯一标识符（类似课程代码）
- 用于导入脚本和API引用，易读易记
- 示例：`"ai_cert_exam"`, `"ml_basic"`
- 优点：跨环境一致，开发/测试/生产可保持相同

#### 新增QuestionSet模型（激进版 - 只保留固定题集）

**用途**：
- 管理固定题集（预导入的固定题目集合，用于考试）
- 追踪题目来源（练习模式中标识"考试题"及其来源）
- ❌ 动态抽取配置不持久化（由Course.default_exam_config提供默认值，由UserSettings提供个性化配置）

```python
class QuestionSet(Base):
    """题集模型（激进版 - 只保留固定题集）"""
    __tablename__ = "question_sets"

    id = Column(String(36), primary_key=True, index=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)  # ✅ 题集代码
    name = Column(String(200), nullable=False)  # 题集名称

    # 固定题集字段
    fixed_question_ids = Column(JSON, nullable=False)  # 固定题集的题目ID列表

    # ❌ 移除：set_type - 只有固定题集，不需要区分
    # ❌ 移除：question_type_config - 动态抽取配置不持久化

    description = Column(Text, nullable=True)  # 题集描述
    total_questions = Column(Integer, default=0)  # 题目总数
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # 关系
    course = relationship("Course", backref="question_sets")

    def __repr__(self):
        return f"<QuestionSet(code='{self.code}' name='{self.name}')>"
```

**QuestionSet特性**：

- **仅支持固定题集**（fixed），不持久化动态抽取配置
- `code`字段：题集的可读唯一标识（类似course_code）
- `fixed_question_ids`：固定题集的题目ID列表

**数据示例**：
```python
# 导入固定题集
question_set = QuestionSet(
    course_id="course-1",
    code="exam_a",
    name="AI认证考试模拟题A卷",
    fixed_question_ids=["q-1", "q-2", "q-3", ...],
    total_questions=50
)
```

#### 新增UserSettings模型（用户设置 - 渐进式）

**用途**：
- 存储用户课程相关的个性化设置
- 考试抽取配置（可覆盖课程默认值）
- 预留扩展空间（未来可添加刷题模式、难度偏好等）

```python
class UserSettings(Base):
    """用户设置模型（0-1阶段：课程相关设置）"""
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True, unique=True)

    # 课程相关设置（JSON结构，灵活扩展）
    course_settings = Column(JSON, nullable=True, default={})
    # 示例结构：
    # {
    #   "course-1": {
    #     "exam_config": {
    #       "question_type_config": {
    #         "single_choice": 20,  # 用户自定义：覆盖默认的30
    #         "multiple_choice": 15,  # 用户自定义：覆盖默认的10
    #         "true_false": 15
    #       },
    #       "difficulty_range": [2, 4]
    #     },
    #     "practice_mode": "sequential"  # 未来扩展：刷题模式偏好
    #   }
    # }

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserSettings(user_id='{self.user_id}')>"
```

**数据结构说明**：
- `course_settings` 是一个字典：`{course_id: settings_object}`
- `settings_object` 可以包含多种设置项：
  - `exam_config`: 考试配置（可覆盖课程默认）
  - `practice_mode`: 刷题模式（未来扩展）
  - `difficulty_preference`: 难度偏好（未来扩展）

**使用示例**：
```python
# 用户对"AI认证考试"有个性化设置
user_settings.course_settings = {
    "course-1": {
        "exam_config": {
            "question_type_config": {
                "single_choice": 20,  # 少于默认的30
                "multiple_choice": 15,  # 多于默认的10
                "true_false": 15
            },
            "difficulty_range": [2, 4]  # 用户偏好中等难度
        }
    }
}
```

**配置优先级设计**：
```
用户请求参数（最高） > 用户设置 > 课程默认 > 硬编码默认（最低）
```

**实施策略**：
- **Phase 1（0-1）**：数据模型支持，暂不提供前端设置界面
- **Phase 2（后续扩展）**：添加用户设置API和前端界面

---

#### 修改Question模型（激进版 - 0-1阶段）

**问题**: 当前Question只有course_type字段，无法关联具体课程
**解决**: 添加course_id外键，建立明确的Course-Question关系

```python
class Question(Base):
    """题目模型（激进版 - 0-1阶段）"""
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, index=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False, index=True)
    # ❌ 移除 course_type - 不再冗余存储，需要时通过Course.course_type获取
    question_type = Column(String(20), nullable=False, index=True)
    content = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)
    correct_answer = Column(String(10), nullable=False, index=True)
    explanation = Column(Text, nullable=True)
    knowledge_points = Column(JSON, nullable=True)
    difficulty = Column(Integer, default=2, nullable=True)
    question_set_ids = Column(JSON, nullable=True, default=list)  # ✅ 记录题目所属的固定题集
    # ... 其他字段

    # 关系
    course = relationship("Course", back_populates="questions")
    records = relationship("UserLearningRecord", back_populates="question")
```

**关键变更**:
- 添加`course_id`外键，关联到具体课程（必须）
- 添加`question_set_ids`字段，记录题目所属的固定题集（练习模式中显示"考试题"来源）
- ❌ **移除`course_type`冗余字段** - 需要时通过JOIN查询`Course.course_type`

**查询示例**（需要course_type时）：
```python
# 如果需要按course_type过滤，使用JOIN
query = db.query(Question).join(Course).filter(
    Course.course_type == "exam",
    Question.course_id == course_id
)

# 如果只需要course_id，直接查询（更常见）
query = db.query(Question).filter(
    Question.course_id == course_id
)
```

**关系定义**:
```python
class Course(Base):
    # ...
    questions = relationship("Question", back_populates="course")
    question_sets = relationship("QuestionSet", backref="course")
```

**性能考虑**（激进方案的权衡）：
- **优点**: 数据模型简洁，减少冗余，易维护
- **缺点**: 需要course_type过滤时使用JOIN，轻微性能影响
- **实际影响**: 可忽略，现代数据库JOIN很快
- **业务场景**: 大多数查询通过course_id直接过滤，不需要course_type

**0-1阶段优势**:
- ✅ 无历史数据，无需迁移脚本
- ✅ 数据模型简洁
- ✅ 导入逻辑简化
- ✅ 维护成本低

**如果后续证明需要course_type冗余**：
- 可以通过数据迁移添加该字段
- 对现有代码无影响

---

#### 修改UserLearningRecord模型（调整艾宾浩斯逻辑）

**问题**：当前无论答对还是答错，都会进入艾宾浩斯记忆曲线

**调整**：
- ✅ 答错：进入艾宾浩斯记忆曲线，计算next_review_time
- ❌ 答对：不进入艾宾浩斯记忆曲线（除非当前已在复习曲线中）
- ✅ 曲线时间按最近一次做错的时间计算

```python
class UserLearningRecord(Base):
    """用户学习记录（调整版）"""
    __tablename__ = "user_learning_records"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False, index=True)
    is_correct = Column(Boolean, nullable=False)
    answer = Column(String(10))
    answered_at = Column(DateTime, default=datetime.utcnow, index=True)
    review_stage = Column(Integer, default=0, index=True)  # 0-7, 8=MASTERED
    next_review_time = Column(DateTime, index=True, nullable=True)  # ✅ 可为空（答对的题不在曲线中）

    # 关系
    question = relationship("Question", back_populates="records")

    def __repr__(self):
        return f"<Record(id='{self.id}' user='{self.user_id}' qid='{self.question_id}' stage={self.review_stage})>"
```

**关键字段调整**：
- `next_review_time`: **可为空**（答对的题不在艾宾浩斯曲线中）

**答题逻辑调整**：

```python
def submit_answer(..., is_correct: bool):
    """
    调整后的答题逻辑
    
    如果答错：
      - 进入/保持在艾宾浩斯记忆曲线
      - 计算next_review_time
    
    如果答对：
      - 如果当前在复习曲线中（review_stage > 0）：保持状态
      - 如果当前不在复习曲线中（review_stage = 0）：不进入曲线
    """
    if not is_correct:
        # 答错：进入艾宾浩斯记忆曲线
        current_stage = record.review_stage or 0
        next_stage, next_review_time = EbbinghausScheduler.calculate_next_review(
            current_stage, is_correct=False
        )
        record.review_stage = next_stage
        record.next_review_time = next_review_time
    else:
        # 答对：不进入艾宾浩斯记忆曲线
        # 保持review_stage不变
        # 不更新next_review_time（保持None或原值）

    # 更新answer和answered_at
    record.is_correct = is_correct
    record.answer = answer
    record.answered_at = now
```

**错题查询逻辑**：
```python
def get_wrong_questions(
    db: Session,
    user_id: str,
    course_id: str = None
) -> List[Question]:
    """
    获取用户的错题列表
    
    定义：
    - 错题：最近一次答题为错的题目（is_correct = False）
    - 如果答对后又答错，以最后一次为准
    """
    # 子查询：获取每个题目的最新记录
    subquery = (
        db.query(
            UserLearningRecord.question_id,
            func.max(UserLearningRecord.answered_at).label('last_answered_at')
        )
        .filter(UserLearningRecord.user_id == user_id)
        .group_by(UserLearningRecord.question_id)
        .subquery()
    )

    # 查询最新记录中is_correct=False的题目
    query = (
        db.query(Question)
        .join(UserLearningRecord, and_(
            UserLearningRecord.question_id == Question.id,
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.is_correct == False,
            UserLearningRecord.answered_at == subquery.c.last_answered_at
        ))
        .filter(Question.is_deleted == False)
    )

    if course_id:
        query = query.filter(Question.course_id == course_id)

    wrong_questions = query.all()
    return wrong_questions
```

**艾宾浩斯复习查询逻辑（调整版）**：
```python
def get_next_question(
    db: Session,
    user_id: str,
    course_id: str = None,  # ✅ 改为course_id
    batch_size: int = 10
) -> List[Question]:
    """
    获取下一批复习题目（调整版）

    优先级（调整后）：
    1. 需要复习的错题（is_correct = False, review_stage > 0, next_review_time <= now）
    2. 用户没刷过的题（review_stage = 0 且 next_review_time = None）

    注意：已答对的题（is_correct = True 且 review_stage = 0）不在复习队列中
    """
    now = datetime.utcnow()

    # 1. 优先：需要复习的错题
    wrong_due_query = (
        db.query(Question)
        .join(UserLearningRecord, UserLearningRecord.question_id == Question.id)
        .filter(
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.is_correct == False,  # 错题
            UserLearningRecord.next_review_time <= now,  # 到期复习
            UserLearningRecord.review_stage > 0,  # 在复习曲线中
            Question.is_deleted == False
        )
    )

    if course_id:
        wrong_due_query = wrong_due_query.filter(Question.course_id == course_id)

    wrong_due_questions = wrong_due_query.limit(batch_size).all()

    if len(wrong_due_questions) >= batch_size:
        return wrong_due_questions

    # 2. 次优先：用户没刷过的题（review_stage = 0 且 next_review_time = None）
    remaining_slots = batch_size - len(wrong_due_questions)

    new_questions_query = (
        db.query(Question)
        .outerjoin(UserLearningRecord, and_(
            UserLearningRecord.question_id == Question.id,
            UserLearningRecord.user_id == user_id
        ))
        .filter(
            or_(
                UserLearningRecord.id == None,  # 从未刷过
                and_(
                    UserLearningRecord.review_stage == 0,
                    UserLearningRecord.next_review_time.is_(None)  # 答对的题，不在曲线中
                )
            ),
            Question.is_deleted == False
        )
    )

    if course_id:
        new_questions_query = new_questions_query.filter(Question.course_id == course_id)

    new_questions = new_questions_query.limit(remaining_slots).all()

    result = wrong_due_questions + new_questions
    return result[:batch_size]
```

---

## 四、实施计划

### 4.1 数据层改造（后端）

#### Step 1: 创建Course模型
- 文件: `src/backend/app/models/course.py`
- 字段定义见3.1节（含default_exam_config）
- 添加到`__init__.py`

#### Step 2: 创建QuestionSet模型
- 文件: `src/backend/app/models/question_set.py`
- 只支持fixed类型（激进版）
- 添加code字段
- 添加到`__init__.py`

#### Step 3: 创建UserSettings模型（Phase 1：数据模型支持）
- 文件: `src/backend/app/models/user_settings.py`
- 添加course_settings字段
- 添加到`__init__.py`

#### Step 4: 修改Question模型
- 文件: `src/backend/app/models/question.py`
- 添加course_id外键（ForeignKey）
- 添加question_set_ids字段（JSON）
- ❌ 移除course_type字段（激进版）
- 添加course关系定义
- 添加到`__init__.py`

#### Step 4.5: 修改UserLearningRecord模型
- 文件: `src/backend/app/models/record.py`
- ✅ 修改next_review_time为可空（答对的题不在艾宾浩斯曲线中）
- 添加到`__init__.py`

#### Step 5: 创建CourseService
- 文件: `src/backend/app/services/course_service.py`
- 方法:
  - `get_courses(active_only=True)`: 获取课程列表
  - `get_course_by_id(course_id)`: 获取课程详情
  - `get_course_by_code(code)`: 根据代码获取课程

#### Step 6: 创建QuestionSetService
- 文件: `src/backend/app/services/question_set_service.py`
- 方法:
  - `get_question_sets(course_id)`: 获取课程的题集列表
  - `get_question_set_by_code(code)`: 根据代码获取题集
  - `validate_question_type_availability(course_id, config)`: 验证题型数量

#### Step 7: 创建UserSettingsService（Phase 1：数据模型支持）
- 文件: `src/backend/app/services/user_settings_service.py`
- 方法:
  - `get_user_settings(user_id)`: 获取用户设置
  - `get_exam_config(user_id, course_id)`: 获取考试配置（优先级：用户设置 > 课程默认 > 硬编码）
  - `update_user_settings(user_id, settings)`: 更新用户设置（Phase 2实现）

#### Step 8: 创建课程API
- 文件: `src/backend/app/api/courses.py`
- 端点:
  - `GET /api/courses/`: 获取课程列表
  - `GET /api/courses/{course_id}`: 获取课程详情
- 注册到main.py

#### Step 9: 创建QuestionSet API
- 文件: `src/backend/app/api/question_sets.py`
- 端点:
  - `GET /api/question-sets/`: 获取题集列表
  - `GET /api/question-sets/{set_code}/questions`: 获取固定题集的题目
- 注册到main.py

#### Step 10: 修改QuizService和ExamService（必须）
- **QuizService**: 修改`start_batch`方法，添加`course_id`参数并筛选题目
- **ExamService**: 修改`start_exam`方法，支持两种考试模式（extraction和fixed_set），使用question_set_code
- **ReviewService**: 修改`get_next_questions`方法，添加`course_id`参数（可选）

**修改示例（QuizService）**:
```python
def start_batch(
    db: Session,
    user_id: str,
    mode: str = "practice",
    batch_size: int = 10,
    course_id: str = None  # 新增必需参数
) -> QuizBatch:
    if not course_id:
        raise ValueError("course_id is required")

    # 根据course_id筛选题目
    query = db.query(Question).filter(
        Question.course_id == course_id,
        Question.is_deleted == False
    )
    # ... 后续逻辑
```

**修改示例（ExamService - extraction模式）**:
```python
def start_exam(
    db: Session,
    user_id: str,
    course_id: str,
    exam_mode: str = "extraction",
    question_type_config: dict = None,
    difficulty_range: list = None,
    question_set_code: str = None  # ✅ 使用code而非ID
) -> QuizBatch:
    """开始考试，支持两种模式"""

    if exam_mode == "extraction":
        # 模式1：动态抽取
        # 获取配置（优先级：请求参数 > 用户设置 > 课程默认 > 硬编码）
        if question_type_config:
            config = {
                "question_type_config": question_type_config,
                "difficulty_range": difficulty_range or [1,5]
            }
        else:
            config = UserSettingsService.get_exam_config(db, user_id, course_id)

        # 验证题型数量
        validation = QuestionSetService.validate_question_type_availability(
            db, course_id, config["question_type_config"]
        )
        if not validation["valid"]:
            raise ValueError(", ".join(validation["errors"]))

        # 按题型抽取题目
        questions = []
        for q_type, count in config["question_type_config"].items():
            query = db.query(Question).filter(
                Question.course_id == course_id,
                Question.question_type == q_type,
                Question.is_deleted == False
            )
            if config.get("difficulty_range"):
                min_diff, max_diff = config["difficulty_range"]
                query = query.filter(
                    Question.difficulty >= min_diff,
                    Question.difficulty <= max_diff
                )
            available = query.all()
            questions.extend(random.sample(available, min(count, len(available))))

    elif exam_mode == "fixed_set":
        # 模式2：固定题集
        if not question_set_code:
            raise ValueError("question_set_code is required for fixed_set mode")

        question_set = QuestionSetService.get_question_set_by_code(
            db, course_id, question_set_code
        )

        if not question_set:
            raise ValueError(f"Question set not found: {question_set_code}")

        question_ids = question_set.fixed_question_ids
        questions = db.query(Question).filter(
            Question.id.in_(question_ids),
            Question.is_deleted == False
        ).all()

    # ... 创建考试批次和答题记录
```

#### Step 11: 数据库初始化
- **创建courses表**: 运行数据库迁移
- **创建question_sets表**: 运行数据库迁移
- **创建user_settings表**: 运行数据库迁移
- **初始化课程数据**: 创建默认课程（含默认配置）

**数据初始化脚本**（0-1阶段，无需迁移）:
```python
# src/scripts/init_course_data.py
def init_course_data(db: Session):
    """初始化课程数据 - 0-1阶段（无历史数据）"""

    # 1. 创建课程
    courses = [
        Course(
            code="ai_cert_exam",
            title="AI认证考试",
            course_type="exam",
            description="AIE55 AI认证考试题库",
            default_exam_config={
                "question_type_config": {
                    "single_choice": 30,
                    "multiple_choice": 10,
                    "true_false": 10
                },
                "difficulty_range": [1, 5]
            },
            is_active=True
        ),
        Course(
            code="ml_basic",
            title="机器学习基础",
            course_type="exam",
            description="机器学习基础刷题",
            default_exam_config={
                "question_type_config": {
                    "single_choice": 20,
                    "multiple_choice": 5,
                    "true_false": 5
                },
                "difficulty_range": [1, 3]
            },
            is_active=True
        )
    ]

    for course in courses:
        db.add(course)

    db.commit()
    print(f"Created {len(courses)} courses")
```

#### Step 11.5: 修改ReviewService（艾宾浩斯调整）
- 文件: `src/backend/app/services/review_service.py`
- 修改`submit_answer`方法：
  - 答错：进入艾宾浩斯记忆曲线，计算next_review_time
  - 答对：不进入艾宾浩斯记忆曲线（除非当前已在复习曲线中）
- 修改`get_next_question`方法：
  - ✅ 优先：需要复习的错题
  - ✅ 次优先：用户没刷过的题
  - ❌ 已答对的题不在复习队列中
- 添加`get_wrong_questions`方法：获取用户的错题列表

#### Step 12: 修改导入脚本（必须）
- **文件**: `src/scripts/import_questions.py`
- **新增参数**:
  - `--course-code`: 课程代码（如"ai_cert_exam"）
  - `--course-id`: 课程ID（优先使用）
  - `--create-course`: 如果课程不存在则自动创建
  - `--create-question-set`: 创建固定题集
  - `--question-set-name`: 题集名称

**导入逻辑**:
```python
def import_questions_from_json(
    db: Session,
    json_file: str,
    course_id: str = None,
    course_code: str = None,
    create_course: bool = True,
    create_question_set: bool = False,
    question_set_name: str = None
):
    """
    导入题目到指定课程，可选创建固定题集

    优先级:
    1. 如果提供了course_id，直接使用
    2. 如果提供了course_code，查找对应课程
    3. 如果create_course=True且course_code存在，创建新课程
    4. 否则报错

    支持多文件导入到同一课程:
    import_questions.py --course-code ai_cert_exam file1.json file2.json file3.json

    支持创建固定题集:
    import_questions.py --course-code ai_cert_exam --create-question-set --question-set-name "模拟题A卷" questions.json
    """
    # 查找课程（必须存在，不支持自动创建）
    course = db.query(Course).filter(
        Course.code == course_code
    ).first()

    if not course:
        raise ValueError(f"Course not found: {course_code}")

    # 导入题目
    questions_data = load_json(json_file)
    question_ids = []

    for q_data in questions_data:
        question = Question(
            course_id=course.id,
            # ✅ 不需要 course_type
            question_type=q_data['question_type'],
            question_set_ids=[],  # 初始化为空列表
            # ... 其他字段
        )
        db.add(question)
        db.flush()
        question_ids.append(question.id)

    db.commit()

    # 如果需要，创建固定题集
    if question_set_code and question_set_name:
        question_set = QuestionSet(
            course_id=course.id,
            code=question_set_code,
            name=question_set_name,
            fixed_question_ids=question_ids,
            total_questions=len(question_ids)
        )
        db.add(question_set)

        # 更新题目的question_set_ids
        for q_id in question_ids:
            question = db.query(Question).filter(Question.id == q_id).first()
            if question:
                question.question_set_ids.append(question_set.id)

        db.commit()
        print(f"Created question set: {question_set_name} with {len(question_ids)} questions")

    print(f"Imported {len(questions_data)} questions to course: {course.title}")
```

**命令行示例**:
```bash
# 导入到指定课程（课程必须已存在）
python import_questions.py --course-code ai_cert_exam questions.json

# 导入并创建固定题集
python import_questions.py --course-code ai_cert_exam \
  --question-set-code exam_a \
  --question-set-name "AI认证考试模拟题A卷" \
  a卷_questions.json

# 多文件导入到同一固定题集
python import_questions.py --course-code ai_cert_exam \
  --question-set-code exam_full \
  --question-set-name "AI认证考试完整题库" \
  单选题.json 多选题.json 判断题.json
```

**激进版导入规则**（0-1阶段）：
- ❌ 不支持`--create-course` - 课程必须预先创建（运行init_course_data.py）
- ❌ 不支持`--course-id` - 统一使用`--course-code`
- ✅ 强制规范：必须通过course-code指定课程

### 4.2 前端页面改造

#### Step 1: 修改API客户端
- 文件: `src/frontend/lib/api.ts`
- 添加课程相关接口:
  - `getCourses(activeOnly?: boolean): Promise<Course[]>`
  - `getCourse(courseId: string): Promise<Course>`
  - `getQuestionSets(courseId: string): Promise<QuestionSet[]>`

#### Step 2: 修改首页
- 文件: `src/frontend/app/page.tsx`
- 将"刷题模式"和"考试模式"合并为"选择课程"
- 调整卡片文案

#### Step 3: 创建课程选择页面
- 文件: `src/frontend/app/courses/page.tsx`
- 组件结构:
  - 导航栏
  - 课程卡片列表
  - 课程卡片组件
- 使用Tailwind CSS样式

#### Step 4: 修改刷题/考试页面
- 文件: `src/frontend/app/quiz/page.tsx`
- 文件: `src/frontend/app/exam/page.tsx`
- 接收URL参数course_id
- 显示课程信息
- 传递course_id到API

#### Step 5: 创建错题本页面
- 文件: `src/frontend/app/mistakes/page.tsx`
- 功能:
  - 显示错题列表（通过Mistakes API获取）
  - 按课程筛选错题
  - 点击题目查看详情和解析
  - "重做"按钮：将错题加入当前批次（复用Quiz API）
- Phase 1简化：
  - 直接使用现有的Quiz API重做错题
  - 不需要专门的错题重做批次逻辑

### 4.3 类型定义

#### Course类型
```typescript
// src/frontend/lib/api.ts
export interface Course {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  course_type: string;
  cover_image?: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
}
```

---

## 五、测试计划

### 5.1 单元测试
- [ ] CourseService测试
- [ ] Course API端点测试

### 5.2 集成测试
- [ ] 课程列表页显示正确
- [ ] 点击课程卡片正确跳转
- [ ] 刷题页面正确显示课程信息
- [ ] 考试页面正确显示课程信息

### 5.3 手动验证
1. 启动前后端服务
2. 访问首页 → 点击"选择课程"
3. 查看课程列表是否正确显示
4. 点击某课程 → 进入刷题页面
5. 验证刷题功能正常
6. 返回首页 → 点击同一课程 → 进入考试页面
7. 验证考试功能正常

---

## 六、风险与依赖

### 6.1 风险
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 时间不足 | 功能不完整 | 优先实现P0功能，P1功能可延后 |
| 现有代码耦合度高 | 改动范围扩大 | 最小化改动方案，避免重构 |
| 前端UI设计耗时 | 界面不够美观 | 使用简单卡片布局，专注功能 |

### 6.2 依赖
- 无外部依赖
- 依赖现有数据库和API架构

---

## 七、成功标准

### 功能完整性
- [ ] 用户可以查看课程列表
- [ ] 用户可以点击课程进入刷题/考试页面
- [ ] 课程信息正确显示
- [ ] 刷题/考试功能保持正常

### 用户体验
- [ ] 流程清晰：首页 → 课程列表 → 刷题
- [ ] 界面简洁：卡片式课程列表
- [ ] 响应快速：API响应时间<500ms

### 代码质量
- [ ] 遵循现有代码规范
- [ ] TypeScript类型完整
- [ ] 无Lint错误
- [ ] 无Console错误

---

## 八、后续扩展

### 阶段2扩展点
1. **完整课程管理**: 后台CRUD界面
2. **课程章节**: 多级章节结构
3. **课程进度**: 学习进度统计
4. **课程推荐**: 个性化推荐算法
5. **课程权限**: 团队课程、公开课程等

### 技术债务
- ~~course_type vs course_id的关联方式~~ ✅ 已在阶段1统一（Question通过course_id关联Course）
- 课程封面图片存储方式（本地 vs CDN）
- 课程数据导入工具（批量导入已支持）

---

## 九、时间估算

| 任务 | 预计工时 | 备注 |
|------|---------|------|
| 数据层改造（后端） | 4.5-5.5小时 | Course+QuestionSet+UserSettings模型+Question修改+UserLearningRecord修改 |
| 服务层改造（后端） | 3.5-4.5小时 | Course+QuestionSet+UserSettings Service + Quiz/Exam/Review修改（艾宾浩斯调整） |
| API层改造（后端） | 2-3小时 | Courses+QuestionSets+Mistakes API + UserSettings API（未来扩展） |
| 数据库初始化 | 0.5小时 | 课程初始化（含默认配置） |
| 导入脚本改造 | 1-1.5小时 | 激进版导入脚本 |
| 前端页面改造 | 2.5-3.5小时 | 首页+课程页+错题本页+修改刷题/考试页 |
| 测试与验证 | 2-2.5小时 | 功能测试+配置优先级测试+艾宾浩斯算法测试+错题本测试 |
| **总计** | **16.5-21小时** | 约2-2.5个工作日 |

---

## 十一、渐进式实施路径

### Phase 1: MVP（当前0-1阶段）

**后端**：
- ✅ 创建Course模型（含default_exam_config）
- ✅ 创建QuestionSet模型（只支持fixed，code字段）
- ✅ 创建UserSettings模型（数据结构支持）
- ✅ 修改Question模型（添加course_id + question_set_ids，移除course_type）
- ✅ 实现配置优先级逻辑（用户设置 > 课程默认 > 硬编码）
- ✅ Exam API支持不传config时使用默认配置
- ❌ 暂不实现UserSettings API（前端不需要）

**前端**：
- ✅ 简化版考试界面（直接使用默认配置）
- ✅ 简化版课程选择页面
- ❌ 暂不实现用户设置界面

**数据初始化**：
- ✅ 课程初始化脚本（含默认配置）
- ✅ 示例默认配置：单选30，多选10，判断10
- ❌ 无需数据迁移脚本（0-1阶段，无历史数据）

**实施优先级**（Phase 1必做）：
1. Course模型 + 初始化脚本
2. Question模型修改
3. QuestionSet模型
4. UserSettings模型（仅数据结构）
5. UserLearningRecord模型修改（艾宾浩斯调整）
6. ReviewService修改（艾宾浩斯调整）
7. 配置优先级逻辑
8. Exam API改造
9. Mistakes API（错题本API）
10. 前端课程选择页面
11. 前端错题本页面（简化版）
12. 前端考试页面改造

**验收标准**（Phase 1）：
- ✅ 用户可以选择课程
- ✅ 考试模式支持动态抽取（使用默认配置）
- ✅ 考试模式支持固定题集
- ✅ 刷题模式显示题目来源（固定题集）
- ✅ 配置优先级正确工作（课程默认）
- ✅ 导入脚本支持课程和固定题集
- ✅ 艾宾浩斯算法调整正确（错题进入曲线，答对不进入）
- ✅ next_review_time可为空（答对的题不在曲线中）
- ✅ 错题本功能正常（显示错题列表，支持筛选）
- ✅ 错题可以重做（复用Quiz API）

---

### Phase 2: 用户个性化（后续扩展）

**后端**：
- ✅ 实现UserSettings API（GET/PUT）
- ✅ 支持更新用户课程设置

**前端**：
- ✅ 用户设置页面（课程个性化配置）
- ✅ 考试模式显示"我的设置"选项
- ✅ 自定义抽取配置界面（可选保存）

**新增功能**：
- 用户可以覆盖课程默认配置
- 保存用户的考试偏好
- 快速使用"我的设置"开始考试
- 错题本高级功能（错题统计、错题练习模式、错题导出）

**实施优先级**（Phase 2）：
1. UserSettings API实现
2. 前端用户设置页面
3. 前端考试页面集成"我的设置"
4. 配置编辑界面
5. 错题本页面高级功能

---

## 十、附录

### 10.1 相关文档
- `核心设计文档.md`: 系统整体设计
- `功能细化设计文档_v1.2.md`: 详细功能设计
- `prompt_rush_exam.md`: 快速开发需求

### 10.2 代码位置索引
- 后端模型: `src/backend/app/models/`
- 后端服务: `src/backend/app/services/`
- 后端API: `src/backend/app/api/`
- 前端页面: `src/frontend/app/`
- 前端API客户端: `src/frontend/lib/api.ts`

---

**文档状态**: ✅ 准备就绪，可开始实施
**最后更新**: 2026-01-20（激进方案 + UserSettings + 错题本 + 艾宾浩斯调整）
**版本**: v4.0 - 激进设计 + UserSettings + 错题本 + 艾宾浩斯调整
  - v1.0: 初始计划文档
  - v2.0: 添加QuestionSet模型和双模式考试系统
  - v3.0: 激进设计 + UserSettings（Phase 1数据模型，Phase 2个性化）
  - v4.0: 错题本模块 + 艾宾浩斯算法调整（错题进入曲线，答对不进入）
