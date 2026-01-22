# Core Module - 核心模块

核心模块提供 AILearn Hub 系统的基础功能，包括数据库配置和艾宾浩斯记忆曲线算法。

## 目录结构

```
app/core/
├── __init__.py
├── database.py      # 数据库配置和连接管理
└── ebbinghaus.py    # 艾宾浩斯记忆曲线算法
```

## 数据库配置 (database.py)

### 功能概述

`database.py` 提供数据库连接和会话管理，支持多种数据库类型：
- SQLite（开发环境，默认）
- PostgreSQL（生产环境）

### 核心组件

#### 1. DATABASE_URL

数据库连接字符串，通过环境变量配置：

```python
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/app.db"  # 默认SQLite
)
```

**配置示例：**

**SQLite（开发环境）：**
```env
DATABASE_URL=sqlite:///./data/app.db
```

**PostgreSQL（生产环境）：**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/ailearn_db
```

#### 2. Engine

SQLAlchemy 数据库引擎：

```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
```

- SQLite 需要额外的 `connect_args` 配置
- PostgreSQL 使用默认配置

#### 3. SessionLocal

数据库会话工厂：

```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

#### 4. get_db() - 依赖注入

FastAPI 依赖注入函数，用于在路由中获取数据库会话：

```python
def get_db():
    """数据库会话依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 使用方法

#### 在 API 路由中使用

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

@router.get("/users/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

#### 在 Service 层中使用

```python
from app.core.database import SessionLocal

class UserService:
    @staticmethod
    def get_user(user_id: str):
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
```

### 数据库初始化

使用项目提供的脚本初始化数据库：

```bash
cd scripts
./init_db.sh
```

详见：[scripts/README.md](../../../scripts/README.md)

## 艾宾浩斯记忆曲线 (ebbinghaus.py)

### 功能概述

`ebbinghaus.py` 实现了基于艾宾浩斯遗忘曲线的复习调度算法，是系统的核心学习算法。

### 复习阶段和间隔

| 阶段 | 名称 | 复习间隔 | 记忆保持率 |
|------|------|---------|-----------|
| 0 | NEW | 0（新题） | 100% |
| 1 | LEVEL_1 | 30分钟 | 85% |
| 2 | LEVEL_2 | 12小时 | 70% |
| 3 | LEVEL_3 | 1天 | 60% |
| 4 | LEVEL_4 | 2天 | 50% |
| 5 | LEVEL_5 | 4天 | 40% |
| 6 | LEVEL_6 | 7天 | 30% |
| 7 | LEVEL_7 | 15天 | 20% |
| 8 | MASTERED | ∞（已掌握） | - |

### 核心算法

#### 1. 复习间隔配置

```python
REVIEW_INTERVALS = {
    0: 0,        # NEW - 新题
    1: 30,       # 30分钟后
    2: 720,      # 12小时
    3: 1440,     # 1天
    4: 2880,     # 2天
    5: 5760,     # 4天
    6: 10080,    # 7天
    7: 21600,    # 15天
}
```

#### 2. calculate_next_review() - 计算下次复习时间

根据当前阶段和答题结果，计算下一阶段和复习时间。

**签名：**
```python
@classmethod
def calculate_next_review(cls, current_stage: int, is_correct: bool)
    -> tuple[int, datetime | None]:
```

**参数：**
- `current_stage`: 当前复习阶段 (0-7)
- `is_correct`: 是否答对

**返回值：**
- `(next_stage, next_review_time)`: 下一阶段和下次复习时间
  - 如果 `next_review_time` 为 `None`，表示已掌握（第8阶段）

**逻辑：**
```python
if is_correct:
    next_stage = min(current_stage + 1, cls.MAX_STAGE)  # 答对：进入下一阶段
else:
    next_stage = 1  # 答错：回到第1阶段

if next_stage == cls.MAX_STAGE:
    return next_stage, None  # 已掌握

interval = cls.REVIEW_INTERVALS[next_stage]
next_time = datetime.utcnow() + timedelta(minutes=interval)
return next_stage, next_time
```

**使用示例：**
```python
from app.core.ebbinghaus import EbbinghausScheduler

# 场景1：新题答对
current_stage = 0
is_correct = True
next_stage, next_time = EbbinghausScheduler.calculate_next_review(current_stage, is_correct)
# next_stage = 1, next_time = 30分钟后

# 场景2：复习题答错
current_stage = 3
is_correct = False
next_stage, next_time = EbbinghausScheduler.calculate_next_review(current_stage, is_correct)
# next_stage = 1, next_time = 30分钟后

# 场景3：最后阶段答对，已掌握
current_stage = 7
is_correct = True
next_stage, next_time = EbbinghausScheduler.calculate_next_review(current_stage, is_correct)
# next_stage = 8, next_time = None
```

#### 3. get_review_priority() - 获取复习优先级

计算复习题目的优先级，用于题目排序。

**签名：**
```python
@classmethod
def get_review_priority(cls, review_stage: int) -> int:
```

**参数：**
- `review_stage`: 复习阶段

**返回值：**
- 优先级分数（数字越小，优先级越高）

**优先级规则：**
1. 错题（`review_stage = 0` 且 `is_correct = False`）
2. 新题（`review_stage = 0` 且 `is_correct = None`）
3. 复习题（`review_stage > 0`，按阶段排序，越早的越优先）

**使用示例：**
```python
# 新题优先级最高
priority = EbbinghausScheduler.get_review_priority(0)  # 返回 0

# 早期复习题次之
priority = EbbinghausScheduler.get_review_priority(1)  # 返回 1

# 晚期复习题优先级较低
priority = EbbinghausScheduler.get_review_priority(7)  # 返回 7
```

### 算法流程

#### 学习流程图

```
新题（阶段0）
    │
    ├─→ 答对 ──────────┐
    │                 ↓
    │              阶段1（30分钟）
    │                 │
    │              [等待30分钟]
    │                 │
    │              [到期可复习]
    │                 │
    ├─→ 答对 ─────────┤
    │                 ↓
    │              阶段2（12小时）
    │                 │
    │              [继续复习流程...]
    │
    └─→ 答错 ─────────┘
                   ↓
               回到阶段1
```

#### 题目推荐逻辑

系统根据以下优先级推荐题目：

1. **需要复习的错题**（优先级最高）
   - 上次答错的题目
   - 需要立即复习

2. **新题**
   - 从未刷过的题目
   - 按难度和题型平衡

3. **到期的复习题**
   - 根据艾宾浩斯间隔到期
   - 按阶段排序，早期优先

4. **未到期的复习题**（最低优先级）

### 在服务中使用

#### 示例：答题后更新复习信息

```python
from app.core.ebbinghaus import EbbinghausScheduler
from datetime import datetime

# 提交答案后
current_stage = record.review_stage
is_correct = (user_answer == question.correct_answer)

# 计算下一阶段
next_stage, next_review_time = EbbinghausScheduler.calculate_next_review(
    current_stage, is_correct
)

# 更新学习记录
record.review_stage = next_stage
record.next_review_time = next_review_time
record.is_correct = is_correct
record.last_review_time = datetime.utcnow()
```

#### 示例：获取待复习题目

```python
from datetime import datetime

def get_due_review_questions(user_id: str, db: Session):
    """获取待复习题目"""
    current_time = datetime.utcnow()

    # 查询到期复习的题目
    due_questions = db.query(LearningRecord).filter(
        LearningRecord.user_id == user_id,
        LearningRecord.next_review_time <= current_time,
        LearningRecord.review_stage < EbbinghausScheduler.MAX_STAGE
    ).all()

    return due_questions
```

### 注意事项

1. **时间处理**
   - 所有时间使用 UTC 时区
   - 使用 `datetime.utcnow()` 获取当前时间

2. **阶段边界**
   - `MAX_STAGE = 8` 表示已掌握
   - 达到第8阶段后不再需要复习

3. **答错重置**
   - 任何阶段答错都回到第1阶段
   - 这确保了错误知识点的及时巩固

4. **间隔单位**
   - 所有间隔以分钟为单位
   - 使用 `timedelta(minutes=...)` 进行时间计算

## 扩展性

### 自定义复习间隔

如果需要自定义复习间隔，可以修改 `REVIEW_INTERVALS` 字典：

```python
REVIEW_INTERVALS = {
    0: 0,
    1: 60,       # 改为1小时
    2: 1440,     # 改为1天
    # ... 其他阶段
}
```

### 自定义优先级算法

可以修改 `get_review_priority()` 方法，实现更复杂的优先级算法：

```python
@classmethod
def get_review_priority(cls, review_stage: int, difficulty: int = 1):
    """考虑难度的优先级算法"""
    base_priority = review_stage
    # 难度越高，优先级越高
    difficulty_bonus = (5 - difficulty) * 2
    return base_priority + difficulty_bonus
```

## 相关文档

- [数据库模型](../models/README.md)
- [复习服务](../services/README.md#review_servicepy)
- [学习记录模型](../models/record.md)

## 参考资料

- [艾宾浩斯遗忘曲线](https://en.wikipedia.org/wiki/Forgetting_curve)
- [间隔重复系统](https://en.wikipedia.org/wiki/Spaced_repetition)
- [SuperMemo 算法](https://www.supermemo.com/en/blog/theory-of-spaced-repetition)
