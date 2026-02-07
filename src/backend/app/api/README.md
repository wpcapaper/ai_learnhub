# API Routes - API 路由

API 路由层定义了 AILearn Hub 系统的 RESTful API 接口，使用 FastAPI 实现。

## 目录结构

```
app/api/
├── __init__.py
├── users.py                 # 用户管理 API
├── courses.py               # 课程管理 API
├── question_sets.py         # 题集管理 API
├── quiz.py                  # 刷题模式 API
├── exam.py                  # 考试模式 API
├── review.py                # 复习调度 API
└── mistakes.py              # 错题管理 API
```

## 设计原则

### 1. RESTful API 设计
- 使用 HTTP 方法语义（GET, POST, PUT, DELETE）
- 资源导向的 URL 设计
- 统一的响应格式

### 2. Pydantic 模型验证
- 使用 Pydantic 模型验证请求/响应
- 自动类型转换和验证
- 生成 OpenAPI 文档

### 3. 依赖注入
- 使用 `Depends()` 注入数据库会话
- 统一的用户认证（通过 `user_id` 查询参数）
- 可复用的依赖函数

### 4. 异常处理
- 使用 `HTTPException` 抛出 HTTP 错误
- 统一的错误响应格式
- 合适的 HTTP 状态码

## API 路由详解

### 用户管理 API (users.py)

#### 创建/获取用户

```http
POST /api/users/
```

**功能：** 获取或创建用户（Dev 模式）

**查询参数：**
- `user_id` (string, 可选): 用户 ID

**请求体：**
```json
{
  "nickname": "张三"  // 可选
}
```

**响应：**
```json
{
  "id": "uuid-string",
  "username": "dev_abc12345",
  "email": "dev_abc12345@local.dev",
  "nickname": "张三",
  "is_temp_user": true,
  "user_level": "beginner",
  "total_study_time": 0,
  "created_at": "2024-01-01T00:00:00",
  "last_login": null
}
```

#### 获取用户信息

```http
GET /api/users/{user_id}
```

**路径参数：**
- `user_id` (string, 必需): 用户 ID

**响应：** 同创建用户响应

#### 列出所有用户

```http
GET /api/users/
```

**查询参数：**
- `include_deleted` (boolean, 可选): 是否包含已删除用户（默认 false）

**响应：**
```json
[
  {
    "id": "uuid-string",
    "username": "user1",
    "email": "user1@example.com",
    "nickname": "用户1",
    "is_temp_user": false,
    "user_level": "intermediate",
    "total_study_time": 3600,
    "created_at": "2024-01-01T00:00:00",
    "last_login": "2024-01-02T00:00:00"
  }
]
```

#### 获取用户统计

```http
GET /api/users/{user_id}/stats
```

**路径参数：**
- `user_id` (string, 必需): 用户 ID

**响应：**
```json
{
  "total_answered": 100,
  "correct_count": 80,
  "accuracy": 80.0,
  "mastered_count": 20,
  "due_review_count": 5
}
```

#### 重置用户数据

```http
POST /api/users/{user_id}/reset
```

**路径参数：**
- `user_id` (string, 必需): 用户 ID

**响应：**
```json
{
  "message": "用户数据已重置"
}
```

#### 删除用户

```http
DELETE /api/users/{user_id}
```

**路径参数：**
- `user_id` (string, 必需): 用户 ID

**查询参数：**
- `soft_delete` (boolean, 可选): 是否软删除（默认 true）

**响应：**
```json
{
  "message": "用户已删除"
}
```

### 课程管理 API (courses.py)

#### 获取课程列表

```http
GET /api/courses/
```

**查询参数：**
- `active_only` (boolean, 可选): 是否只返回启用的课程（默认 true）
- `user_id` (string, 可选): 用户 ID（用于返回用户进度）

**响应：**
```json
[
  {
    "id": "uuid-string",
    "code": "ai_cert_exam",
    "title": "AI 认证考试",
    "description": "人工智能认证考试题库",
    "course_type": "exam",
    "cover_image": "https://...",
    "is_active": true,
    "sort_order": 1,
    "created_at": "2024-01-01T00:00:00",
    "total_questions": 1500,
    "answered_questions": 500,
    "current_round": 2,
    "total_rounds_completed": 1
  }
]
```

#### 获取课程详情

```http
GET /api/courses/{course_id}
```

**路径参数：**
- `course_id` (string, 必需): 课程 ID

**响应：** 同课程列表中的单个课程对象

### 题集管理 API (question_sets.py)

#### 获取题集列表

```http
GET /api/question-sets/
```

**查询参数：**
- `course_id` (string, 必需): 课程 ID
- `active_only` (boolean, 可选): 是否只返回启用的题集（默认 true）

**响应：**
```json
[
  {
    "id": "uuid-string",
    "course_id": "course-uuid",
    "code": "set1",
    "name": "基础题集",
    "description": "机器学习基础知识",
    "total_questions": 100,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### 获取题集题目

```http
GET /api/question-sets/{code}/questions
```

**路径参数：**
- `code` (string, 必需): 题集代码

**响应：**
```json
[
  {
    "id": "uuid-string",
    "content": "题目内容",
    "question_type": "single_choice",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct_answer": "A",
    "explanation": "...",
    "difficulty": 2,
    "question_set_codes": ["基础题集"]
  }
]
```

### 刷题模式 API (quiz.py)

#### 开始批次刷题

```http
POST /api/quiz/start
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**请求体：**
```json
{
  "mode": "practice",          // "practice" | "exam"
  "batch_size": 10,          // 批次大小（默认 10）
  "course_id": "course-uuid"  // 课程 ID（必需）
}
```

**响应：**
```json
{
  "id": "batch-uuid",
  "user_id": "user-uuid",
  "batch_size": 10,
  "mode": "practice",
  "round_number": 1,
  "started_at": "2024-01-01T00:00:00",
  "status": "in_progress"
}
```

#### 提交批次答案

```http
POST /api/quiz/{batch_id}/answer
```

**路径参数：**
- `batch_id` (string, 必需): 批次 ID

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**请求体：**
```json
{
  "question_id": "question-uuid",
  "answer": "A"
}
```

**响应：**
```json
{
  "id": "answer-uuid",
  "question_id": "question-uuid",
  "user_answer": "A",
  "answered_at": "2024-01-01T00:00:00"
}
```

#### 完成批次

```http
POST /api/quiz/{batch_id}/finish
```

**路径参数：**
- `batch_id` (string, 必需): 批次 ID

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**请求体：**
```json
{}
```

**响应：**
```json
{
  "batch_id": "batch-uuid",
  "total": 10,
  "correct": 8,
  "wrong": 2,
  "accuracy": 80.0
}
```

#### 获取批次题目

```http
GET /api/quiz/{batch_id}/questions
```

**路径参数：**
- `batch_id` (string, 必需): 批次 ID

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**响应：**
```json
[
  {
    "id": "question-uuid",
    "content": "题目内容",
    "question_type": "single_choice",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct_answer": "A",        // 仅批次完成后显示
    "explanation": "...",         // 仅批次完成后显示
    "user_answer": "A",
    "is_correct": true,          // 仅批次完成后显示
    "answered_at": "2024-01-01T00:00:00",
    "question_set_codes": ["基础题集"]
  }
]
```

**注意：**
- 批次进行中：不显示 `correct_answer`, `explanation`, `is_correct`
- 批次完成后：显示所有字段

#### 列出批次

```http
GET /api/quiz/batches
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID
- `limit` (integer, 可选): 限制数量（默认 50）

**响应：**
```json
[
  {
    "id": "batch-uuid",
    "user_id": "user-uuid",
    "batch_size": 10,
    "mode": "practice",
    "round_number": 1,
    "started_at": "2024-01-01T00:00:00",
    "completed_at": "2024-01-01T01:00:00",
    "status": "completed"
  }
]
```

### 考试模式 API (exam.py)

#### 开始考试

```http
POST /api/exam/start
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**请求体：**
```json
{
  "total_questions": 50,                   // 总题目数（动态抽取模式使用）
  "difficulty_range": [1, 5],            // 难度范围（动态抽取模式使用）
  "course_id": "course-uuid",           // 课程 ID（必需）
  "question_set_id": "set1"             // 固定题集代码（固定题集模式使用）
}
```

**响应：**
```json
{
  "exam_id": "batch-uuid",
  "total_questions": 50,
  "mode": "exam",
  "started_at": "2024-01-01T00:00:00",
  "status": "in_progress"
}
```

#### 提交考试答案

```http
POST /api/exam/{exam_id}/answer
```

**路径参数：**
- `exam_id` (string, 必需): 考试 ID

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**请求体：**
```json
{
  "question_id": "question-uuid",
  "answer": "A"
}
```

**响应：**
```json
{
  "id": "answer-uuid",
  "question_id": "question-uuid",
  "user_answer": "A",
  "answered_at": "2024-01-01T00:00:00"
}
```

#### 完成考试

```http
POST /api/exam/{exam_id}/finish
```

**路径参数：**
- `exam_id` (string, 必需): 考试 ID

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**请求体：**
```json
{}
```

**响应：**
```json
{
  "batch_id": "batch-uuid",
  "total": 50,
  "correct": 40,
  "wrong": 10,
  "score": 80.0
}
```

#### 获取考试题目

```http
GET /api/exam/{exam_id}/questions
```

**路径参数：**
- `exam_id` (string, 必需): 考试 ID

**查询参数：**
- `user_id` (string, 必需): 用户 ID
- `show_answers` (boolean, 可选): 是否显示答案（默认 false）

**响应：** 同刷题模式题目格式

### 复习调度 API (review.py)

#### 获取下一批复习题目

```http
GET /api/review/next
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID
- `course_type` (string, 可选): 课程类型（默认 "exam"）
- `batch_size` (integer, 可选): 批次大小（默认 10）

**响应：**
```json
[
  {
    "id": "question-uuid",
    "content": "题目内容",
    "question_type": "single_choice",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct_answer": null,  // 不显示正确答案
    "explanation": null,       // 不显示解析
    "user_answer": null,
    "is_correct": null,
    "answered_at": null
  }
]
```

#### 提交答案

```http
POST /api/review/submit
```

**请求体：**
```json
{
  "user_id": "user-uuid",
  "question_id": "question-uuid",
  "answer": "A",
  "is_correct": true
}
```

**响应：**
```json
{
  "record_id": "record-uuid",
  "review_stage": 1,
  "next_review_time": "2024-01-01T00:30:00",
  "message": "答案已提交"
}
```

#### 获取复习统计

```http
GET /api/review/stats
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**响应：**
```json
{
  "due_count": 5,
  "mastered_count": 20
}
```

#### 获取复习队列

```http
GET /api/review/queue
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID
- `limit` (integer, 可选): 限制数量（默认 100）

**响应：**
```json
[
  {
    "question": {
      "id": "question-uuid",
      "content": "题目内容",
      "question_type": "single_choice",
      ...
    },
    "record": {
      "id": "record-uuid",
      "is_correct": null,
      "review_stage": 1,
      "next_review_time": "2024-01-01T00:30:00",
      "answered_at": null
    }
  }
]
```

#### 获取已掌握题目

```http
GET /api/review/mastered
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID

**响应：**
```json
[
  {
    "id": "question-uuid",
    "content": "题目内容",
    "question_type": "single_choice",
    ...
  }
]
```

### 错题管理 API (mistakes.py)

#### 获取错题列表

```http
GET /api/mistakes/
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID
- `course_id` (string, 可选): 课程 ID

**响应：**
```json
[
  {
    "id": "question-uuid",
    "content": "题目内容",
    "question_type": "single_choice",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct_answer": "A",
    "explanation": "...",
    "last_wrong_time": "2024-01-01T00:00:00"
  }
]
```

#### 获取错题统计

```http
GET /api/mistakes/stats
```

**查询参数：**
- `user_id` (string, 必需): 用户 ID
- `course_id` (string, 可选): 课程 ID

**响应：**
```json
{
  "total_wrong": 10,
  "wrong_by_course": {
    "AI 认证考试": 8,
    "机器学习基础": 2
  },
  "wrong_by_type": {
    "single_choice": 6,
    "multiple_choice": 3,
    "true_false": 1
  }
}
```

#### 重试错题

```http
POST /api/mistakes/retry
```

**请求体：**
```json
{
  "user_id": "user-uuid",
  "course_id": "course-uuid",  // 可选
  "batch_size": 10             // 批次大小（默认 10）
}
```

**响应：**
```json
{
  "batch_id": "batch-uuid",
  "questions": [
    {
      "id": "question-uuid",
      "content": "题目内容",
      ...
    }
  ]
}
```

## 通用规范

### 认证方式

Dev 模式下，通过 `user_id` 查询参数进行身份验证：

```http
GET /api/users/{user_id}?user_id=actual_user_id
POST /api/users/?user_id=actual_user_id
```

### 统一响应格式

#### 成功响应
```json
{
  "data": {...}
}
```

#### 错误响应
```json
{
  "detail": "错误描述"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

### 分页

对于列表查询，使用 `limit` 参数限制返回数量：

```http
GET /api/quiz/batches?user_id=xxx&limit=50
```

### 时间格式

所有时间使用 ISO 8601 格式（UTC 时区）：

```
2024-01-01T00:00:00
```

## Pydantic 模型

### 请求模型

#### UserCreateRequest
```python
class UserCreateRequest(BaseModel):
    nickname: Optional[str] = None
```

#### BatchStartRequest
```python
class BatchStartRequest(BaseModel):
    mode: str = "practice"
    batch_size: int = 10
    course_id: str
```

#### ExamStartRequest
```python
class ExamStartRequest(BaseModel):
    total_questions: int = 50
    difficulty_range: Optional[List[int]] = None
    course_id: str
    question_set_id: Optional[str] = None
```

#### AnswerSubmission
```python
class AnswerSubmission(BaseModel):
    question_id: str
    answer: str
```

### 响应模型

#### UserResponse
```python
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    nickname: Optional[str]
    is_temp_user: bool
    user_level: Optional[str]
    total_study_time: int
    created_at: Optional[datetime]
    last_login: Optional[datetime]
```

#### UserStatsResponse
```python
class UserStatsResponse(BaseModel):
    total_answered: int
    correct_count: int
    accuracy: float
    mastered_count: int
    due_review_count: int
```

#### QuizResult
```python
class QuizResult(BaseModel):
    batch_id: str
    total: int
    correct: int
    wrong: int
    accuracy: float
```

## 扩展指南

### 添加新的 API 路由

1. 创建路由文件：

```python
# app/api/new_resource.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services import NewService

router = APIRouter(prefix="/new-resource", tags=["新资源"])

class NewResourceRequest(BaseModel):
    name: str

class NewResourceResponse(BaseModel):
    id: str
    name: str

@router.post("/", response_model=NewResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_new_resource(
    request: NewResourceRequest,
    user_id: str,  # Dev 模式认证
    db: Session = Depends(get_db)
):
    """创建新资源"""
    # 业务逻辑
    resource = NewService.create(db, request.name)
    return resource

@router.get("/{resource_id}", response_model=NewResourceResponse)
async def get_new_resource(
    resource_id: str,
    db: Session = Depends(get_db)
):
    """获取资源"""
    resource = NewService.get(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    return resource
```

2. 在 `main.py` 中注册路由：

```python
from app.api import new_resource

app.include_router(new_resource.router, prefix="/api", tags=["新资源"])
```

3. 测试 API：

```bash
# 创建资源
curl -X POST http://localhost:8000/api/new-resource/ \
  -H "Content-Type: application/json" \
  -d '{"name": "测试资源"}'

# 获取资源
curl http://localhost:8000/api/new-resource/{resource_id}
```

## 错误处理

### HTTPException

FastAPI 的标准异常类：

```python
from fastapi import HTTPException, status

# 资源不存在
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="用户不存在"
)

# 参数错误
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="无效的参数"
)

# 服务器错误
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="服务器内部错误"
)
```

## 测试

### 手动测试

访问 Swagger UI 进行交互式测试：
- http://localhost:8000/docs

### 使用 curl 测试

```bash
# 创建用户
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"nickname": "张三"}'

# 获取用户
curl http://localhost:8000/api/users/{user_id}

# 开始批次
curl -X POST "http://localhost:8000/api/quiz/start?user_id={user_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "practice",
    "batch_size": 10,
    "course_id": "course-uuid"
  }'
```

## 相关文档

- [数据模型](../models/README.md)
- [业务服务](../services/README.md)
- [核心模块](../core/README.md)
- [后端 README](../README.md)

## OpenAPI 文档

自动生成的 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

完整的 OpenAPI 规范：
- http://localhost:8000/openapi.json
