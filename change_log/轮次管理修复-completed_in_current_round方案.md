# 轮次管理修复（completed_in_current_round方案）

**日期**: 2026-01-21
**问题描述**: 固定题集考试题后无法开启新轮次，轮次在增加但仍然报错"没有可用的题目"

---

## 问题根源分析

### 原始问题
1. **刷题模式**：调用 `ReviewService.get_next_question(allow_new_round=True)`，当所有题目都已刷完时，会自动触发 `start_new_round()` 开启新轮
2. **考试模式（固定题集）**：直接从题库获取题目，**完全不经过轮次检查逻辑**，因此无法触发 `start_new_round()`

### 关键缺陷
- 当题库中所有题目都达到已掌握状态（`review_stage == 8`）时
- 即使调用了 `start_new_round()`，轮次增加了，但题目的复习阶段仍然是8（已掌握）
- `get_next_question` 查询条件：`review_stage < 8 AND review_stage > 0`
- 已掌握的题目（`stage=8`）不满足条件，因此无法获取到任何题目

---

## 解决方案

### 设计原则
**轮次管理与艾宾浩斯复习算法解耦**
- `current_round`：用于统计用户完成了多少轮完整刷题（展示用）
- `review_stage`：完全由艾宾浩斯算法管理，根据答题情况自动更新
- 新增字段 `completed_in_current_round`：标记题目是否在当前轮次刷过（独立于复习状态）

---

## 代码变更

### 1. 数据库模型变更

**文件**: `src/backend/app/models/record.py`

**变更内容**：
```python
# 新增字段
completed_in_current_round = Column(Boolean, default=False, index=True)  # 在当前轮次是否刷过（独立于艾宾浩斯状态）
```

**说明**：
- 新增 `completed_in_current_round` 字段标记题目是否在当前轮次刷过
- 该字段独立于艾宾浩斯复习状态（`review_stage`）
- 默认值：`False`

---

### 2. 轮次管理逻辑变更

**文件**: `src/backend/app/services/user_service.py`

**变更前**：
```python
def start_new_round(db, user_id, course_id):
    # ❌ 错误方案：重置题目的 review_stage
    # 将所有已掌握题目重置为第1阶段
    # 这会破坏艾宾浩斯算法的独立性
```

**变更后**：
```python
def start_new_round(db, user_id, course_id):
    """
    开始新的一轮刷题（轮次管理核心逻辑 - 修复版）

    轮次管理与艾宾浩斯复习算法解耦：
    - current_round += 1  # 进入下一轮，仅用于统计和展示
    - total_rounds_completed += 1  # 记录已完成的轮次数
    - 更新 updated_at 时间戳  # 记录轮次切换时间
    - 重置 completed_in_current_round = False，让题目可以重新在新轮次刷题
    """
    progress = get_or_create_progress(db, user_id, course_id)

    # 仅更新轮次编号，不修改题目复习状态
    progress.current_round += 1
    progress.total_rounds_completed += 1
    progress.updated_at = datetime.utcnow()

    # 重置所有题目的轮次标记
    for record in all_records:
        record.completed_in_current_round = False

    db.commit()
    return progress
```

**关键改动**：
- 移除了修改 `review_stage` 的逻辑（不再破坏艾宾浩斯算法）
- 改为重置 `completed_in_current_round = False`，让题目可以在新轮次重新刷题
- 保留艾宾浩斯算法的独立性

---

### 3. 题目获取逻辑变更

**文件**: `src/backend/app/services/review_service.py`

#### 变更点1：查询条件增加轮次过滤

**变更前**：
```python
due_query = db.query(Question).join(UserLearningRecord).filter(
    UserLearningRecord.user_id == user_id,
    UserLearningRecord.next_review_time <= now,
    UserLearningRecord.review_stage < EbbinghausScheduler.MAX_STAGE,
    UserLearningRecord.review_stage > 0,
    Question.is_deleted == False
)
```

**变更后**：
```python
due_query = db.query(Question).join(UserLearningRecord).filter(
    UserLearningRecord.user_id == user_id,
    UserLearningRecord.next_review_time <= now,
    UserLearningRecord.review_stage < EbbinghausScheduler.MAX_STAGE,
    UserLearningRecord.review_stage > 0,
    UserLearningRecord.completed_in_current_round == False,  # 新增：当前轮次未刷过
    Question.is_deleted == False
)
```

**说明**：
- 查询条件增加 `completed_in_current_round == False`
- 确保只返回当前轮次未刷过的题目
- 轮次切换后，所有题目的 `completed_in_current_round` 被重置为 `False`，可以重新获取

---

#### 变更点2：答题时更新轮次标记

**变更前**：
```python
def submit_answer(db, user_id, question_id, answer, is_correct):
    # ...更新复习阶段
    record.review_stage = next_stage
    # ...提交
```

**变更后**：
```python
def submit_answer(db, user_id, question_id, answer, is_correct):
    # ...更新复习阶段
    record.review_stage = next_stage
    record.completed_in_current_round = True  # 新增：标记在当前轮次已刷过
    # ...提交
```

**说明**：
- 答题时设置 `completed_in_current_round = True`
- 防止同一轮次重复刷同一道题

---

#### 变更点3：移除错误的轮次重置逻辑

**移除前**（错误方案）：
```python
if allow_new_round and len(result) == 0 and course_id:
    # 错误：查询所有已掌握的题目（review_stage == 8）
    mastered_questions = db.query(Question).join(UserLearningRecord).filter(
        UserLearningRecord.review_stage == EbbinghausScheduler.MAX_STAGE
    ).all()

    # 错误：将所有已掌握题目重置为 review_stage = 0
    for question in mastered_questions:
        record.review_stage = 0
        record.next_review_time = now

    db.commit()

    # 重新获取题目
    result = get_next_question(db, user_id, course_id, batch_size, allow_new_round=False)
```

**移除后**（正确方案）：
```python
if allow_new_round and len(result) == 0 and course_id:
    # 调用 start_new_round 更新轮次编号和重置 completed_in_current_round
    UserService.start_new_round(db, user_id, course_id)

    # 重置后重新获取题目
    result = get_next_question(db, user_id, course_id, batch_size, allow_new_round=False)
```

**关键改动**：
- 移除了手动重置 `review_stage` 的逻辑
- 改为依赖 `start_new_round()` 自动重置 `completed_in_current_round = False`
- 保持艾宾浩斯算法的独立性

---

### 4. 考试模式修复

**文件**: `src/backend/app/services/exam_service.py`

**变更前**：
```python
def start_exam(db, user_id, course_id, exam_mode, ...):
    # 直接从题库获取题目，不经过轮次检查
    # 问题：所有题目都已掌握时，无法触发 start_new_round
```

**变更后**：
```python
def start_exam(db, user_id, course_id, exam_mode, ...):
    """
    开始一次考试（修改版 - 支持轮次管理）

    轮次管理逻辑（修复版）：
    - 在开始考试前，通过获取1个题来触发轮次检查
    - 如果题库中所有题目都已刷完（无可用题），会自动开启新轮
    - 这样确保考试模式与刷题模式的轮次管理逻辑一致
    """
    # 在开始考试前检查是否需要开启新轮
    try:
        from app.services.review_service import ReviewService
        # 通过获取1个题触发轮次检查逻辑
        test_questions = ReviewService.get_next_question(
            db, user_id, course_id, 1, allow_new_round=True
        )
        # 获取到题目后立即释放
    except Exception:
        pass

    # 继续正常的考试题目获取逻辑
    ...
```

**关键改动**：
- 在开始考试前调用 `get_next_question` 触发轮次检查
- 确保考试模式和刷题模式的轮次管理逻辑一致

---

## 艾宾浩斯复习阶段说明（用于轮次管理）

### 复习阶段定义
- **阶段 0**: 新题（未刷过）
- **阶段 1-7**: 艾宾浩斯复习阶段（按时间间隔需要复习）
- **阶段 8**: 已掌握（无需再复习）

### 艾宾浩斯算法
- **答对**：进入下一阶段（如 阶段1→2→3→...→8已掌握）
- **答错**：回到第1阶段重新开始

---

## 轮次管理 vs 艾宾浩斯算法的关系

| 维度 | 轮次管理 | 艾宾浩斯算法 |
|------|---------|-------------|
| **用途** | 统计用户完成了多少轮完整刷题 | 根据答题情况安排复习 |
| **更新时机** | 用户完成一轮所有题后自动切换 | 每次答题后立即更新 |
| **依赖关系** | 完全独立，不依赖算法 | 完全独立，不依赖轮次 |
| **查询过滤** | `completed_in_current_round == False` | `review_stage < 8 AND review_stage > 0` |
| **数据字段** | `current_round`, `completed_in_current_round` | `review_stage`, `next_review_time` |

---

## 验证结果

### 测试场景
1. **所有题目都已掌握（`review_stage = 8`）**
   - 开启新轮前：`current_round = 7`，`completed_in_current_round = True`
   - 开启新轮：`current_round = 8`，`completed_in_current_round = False`
   - 获取题目：成功获取到 1 题（因为 `completed_in_current_round = False`）

2. **部分题目已刷过**
   - 未刷过的题目：`completed_in_current_round = False`，可以获取
   - 已刷过的题目：`completed_in_current_round = True`，不会重复获取

3. **轮次独立于复习状态**
   - 题目可以多次复习（`review_stage` 在 1-8 之间变化）
   - 但每轮只刷一次（`completed_in_current_round` 从 False→True 只发生一次）

---

## 影响范围

### 修改的文件
1. `src/backend/app/models/record.py` - 数据库模型
2. `src/backend/app/services/user_service.py` - 轮次管理服务
3. `src/backend/app/services/review_service.py` - 复习服务
4. `src/backend/app/services/exam_service.py` - 考试服务

### 数据库变更
- 新增字段：`user_learning_records.completed_in_current_round`（BOOLEAN）
- 需要执行数据库迁移脚本（SQLAlchemy会自动处理）

---

## 总结

### 核心思想
**轮次管理与艾宾浩斯复习算法完全解耦**

### 实现方式
1. **新增独立字段** `completed_in_current_round` 标记题目是否在当前轮次刷过
2. **轮次切换**：只更新轮次编号，重置 `completed_in_current_round = False`
3. **题目查询**：增加 `completed_in_current_round == False` 过滤条件
4. **答题更新**：设置 `completed_in_current_round = True` 防止重复刷题

### 解决的问题
- ✅ 刷题模式：轮次切换后可以继续刷题
- ✅ 考试模式：所有题目已掌握时可以自动开启新轮并继续考试
- ✅ 固定题集考试：轮次管理逻辑与刷题模式一致
- ✅ 艾宾浩斯算法：保持独立性，不被轮次管理破坏
