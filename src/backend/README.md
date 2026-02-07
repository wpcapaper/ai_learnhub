# AILearn Hub - Backend

基于 FastAPI 的 AI 学习系统后端服务，实现刷题、考试、复习调度等功能。

## 项目概述

AILearn Hub 后端是一个智能学习系统的 RESTful API 服务，核心功能包括：
- **用户管理**：支持 Dev 模式免注册快速体验
- **课程管理**：多课程、多题集支持
- **刷题模式**：批次刷题，支持艾宾浩斯智能复习
- **考试模式**：模拟真实考试，支持固定题集和动态抽取
- **复习调度**：基于艾宾浩斯记忆曲线的智能推荐
- **错题管理**：错题记录和针对性练习

## 技术栈

### 核心框架
- **FastAPI**: 现代、快速的 Web 框架
  - 自动生成 OpenAPI 文档
  - 类型验证（Pydantic）
  - 异步支持

### 数据库
- **SQLAlchemy**: Python ORM
- **数据库支持**:
  - SQLite（开发环境，默认）
  - PostgreSQL（生产环境）

### Python 版本
- Python 3.11+

## 目录结构

```
src/backend/
├── main.py                 # FastAPI 应用入口
├── pyproject.toml         # 项目依赖配置
├── Dockerfile             # Docker 构建文件
├── .dockerignore          # Docker 忽略文件
├── data/                  # 数据库文件目录（SQLite）
│   ├── app.db            # 应用数据库
│   └── ailearn.db        # 学习数据库（如果有）
├── app/
│   ├── __init__.py
│   ├── core/             # 核心模块
│   │   ├── database.py   # 数据库配置和连接
│   │   └── ebbinghaus.py # 艾宾浩斯记忆曲线算法
│   ├── models/           # 数据模型（SQLAlchemy）
│   │   ├── __init__.py
│   │   ├── base.py       # Base 类定义
│   │   ├── user.py       # 用户模型
│   │   ├── course.py     # 课程模型
│   │   ├── question.py   # 题目模型
│   │   ├── question_set.py  # 题集模型
│   │   ├── batch.py      # 批次模型（刷题/考试）
│   │   ├── record.py     # 学习记录模型
│   │   ├── answer_history.py  # 答题历史
│   │   ├── user_course_progress.py  # 用户课程进度
│   │   └── user_settings.py  # 用户设置
│   ├── services/         # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── user_service.py           # 用户服务
│   │   ├── course_service.py         # 课程服务
│   │   ├── question_set_service.py   # 题集服务
│   │   ├── quiz_service.py           # 刷题服务
│   │   ├── exam_service.py           # 考试服务
│   │   ├── review_service.py        # 复习服务
│   │   └── user_settings_service.py  # 用户设置服务
│   └── api/              # API 路由
│       ├── __init__.py
│       ├── users.py           # 用户管理 API
│       ├── courses.py         # 课程管理 API
│       ├── question_sets.py   # 题集管理 API
│       ├── quiz.py            # 刷题模式 API
│       ├── exam.py            # 考试模式 API
│       ├── review.py          # 复习调度 API
│       └── mistakes.py        # 错题管理 API
└── requirements.txt       # 依赖列表（可选）
```

## 快速开始

### 环境要求

- Python 3.11+
- pip 或 uv（推荐）

### 安装依赖

**使用 pip：**
```bash
cd src/backend
pip install -r requirements.txt
```

**使用 uv（推荐，更快）：**
```bash
cd src/backend
uv pip install -r requirements.txt
# 或使用 uv sync（如果有 pyproject.toml）
uv sync
```

### 配置环境变量

创建 `.env` 文件（可选）：

```env
# 数据库配置
DATABASE_URL=sqlite:///./data/app.db

# 或者使用 PostgreSQL
# DATABASE_URL=postgresql://user:password@localhost:5432/ailearn_db

# 应用配置
SECRET_KEY=your-secret-key-here
DEV_MODE=true
```

### 启动开发服务器

```bash
cd src/backend

# 使用 uvicorn 直接启动
uvicorn main:app --host 0.0.0.0 --reload --port 8000
```

服务启动后：
- API 地址：http://localhost:8000
- API 文档：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

### 健康检查

```bash
curl http://localhost:8000/health
```

返回：
```json
{
  "status": "healthy"
}
```

## 开发指南

### 数据库初始化

使用项目提供的脚本进行数据库初始化：

```bash
cd ../scripts

# 初始化数据库表
./init_db.sh

# 初始化课程数据
./init_course_data.sh

# 导入题目
./import_questions.sh ../data/converted/all_questions.json
```

详细脚本使用说明见：[scripts/README.md](../../scripts/README.md)

### 添加新的 API 路由

1. 在 `app/api/` 创建新的路由文件，例如 `items.py`：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter(prefix="/items", tags=["项目管理"])

@router.get("/")
async def list_items(db: Session = Depends(get_db)):
    """获取项目列表"""
    return {"items": []}

@router.post("/")
async def create_item(item_data: dict, db: Session = Depends(get_db)):
    """创建项目"""
    return {"message": "Item created"}
```

2. 在 `main.py` 中注册路由：

```python
from app.api import items

app.include_router(items.router, prefix="/api", tags=["项目管理"])
```

### 添加新的数据模型

1. 在 `app/models/` 创建新的模型文件，例如 `item.py`：

```python
from sqlalchemy import Column, String, Integer
from app.models.base import Base

class Item(Base):
    """项目模型"""
    __tablename__ = "items"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
```

2. 在 `app/models/__init__.py` 中导入模型：

```python
from .item import Item
```

### 添加新的业务逻辑服务

在 `app/services/` 创建服务文件，例如 `item_service.py`：

```python
from sqlalchemy.orm import Session
from app.models.item import Item

class ItemService:
    """项目业务逻辑"""

    @staticmethod
    def create_item(db: Session, name: str, description: str = None):
        """创建项目"""
        item = Item(id=str(uuid.uuid4()), name=name, description=description)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def get_items(db: Session, skip: int = 0, limit: int = 100):
        """获取项目列表"""
        return db.query(Item).offset(skip).limit(limit).all()
```

## API 文档

### 基础信息

- **Base URL**: `http://localhost:8000`
- **认证方式**: Dev 模式下通过 `user_id` 查询参数

### 用户管理 API (`/api/users`)

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/users/` | 获取或创建用户 |
| GET | `/api/users/{user_id}` | 获取用户信息 |
| GET | `/api/users/` | 列出所有用户 |
| GET | `/api/users/{user_id}/stats` | 获取用户统计 |
| DELETE | `/api/users/{user_id}` | 删除用户 |
| POST | `/api/users/{user_id}/reset` | 重置用户数据 |

### 课程管理 API (`/api/courses`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/courses/` | 获取课程列表 |
| GET | `/api/courses/{course_id}` | 获取课程详情 |

### 题集管理 API (`/api/question-sets`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/question-sets/` | 获取题集列表 |
| GET | `/api/question-sets/{code}/questions` | 获取题集题目 |

### 刷题模式 API (`/api/quiz`)

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/quiz/start` | 开始批次刷题 |
| POST | `/api/quiz/{batch_id}/answer` | 提交批次答案 |
| POST | `/api/quiz/{batch_id}/finish` | 完成批次 |
| GET | `/api/quiz/{batch_id}/questions` | 获取批次题目 |
| GET | `/api/quiz/batches` | 列出批次 |
| GET | `/api/quiz/{batch_id}` | 获取批次详情 |

### 考试模式 API (`/api/exam`)

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/exam/start` | 开始考试 |
| POST | `/api/exam/{exam_id}/answer` | 提交考试答案 |
| POST | `/api/exam/{exam_id}/finish` | 完成考试 |
| GET | `/api/exam/{exam_id}/questions` | 获取考试题目 |

### 复习调度 API (`/api/review`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/review/next` | 获取下一批复习题目 |
| POST | `/api/review/submit` | 提交答案并更新进度 |
| GET | `/api/review/stats` | 获取复习统计 |
| GET | `/api/review/queue` | 获取复习队列 |

### 错题管理 API (`/api/mistakes`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/mistakes/` | 获取错题列表 |
| GET | `/api/mistakes/stats` | 获取错题统计 |
| POST | `/api/mistakes/retry` | 重试错题 |

完整 API 文档请访问：http://localhost:8000/docs

## 核心模块说明

### 艾宾浩斯记忆曲线 (`app/core/ebbinghaus.py`)

实现基于艾宾浩斯遗忘曲线的复习调度算法：

**复习阶段和间隔：**
- 阶段 0：新题
- 阶段 1：30分钟后
- 阶段 2：12小时后
- 阶段 3：1天后
- 阶段 4：2天后
- 阶段 5：4天后
- 阶段 6：7天后
- 阶段 7：15天后
- 阶段 8：已掌握

**规则：**
- 答对：进入下一阶段
- 答错：回到第1阶段重新开始

### 数据库配置 (`app/core/database.py`)

支持多种数据库：
- SQLite（开发环境）
- PostgreSQL（生产环境）

使用 SQLAlchemy ORM 进行数据库操作。

## Docker 部署

### 构建镜像

```bash
cd src/backend
docker build -t ailearn-backend .
```

### 运行容器

```bash
docker run -p 8000:8000 -e DATABASE_URL=sqlite:///./data/app.db ailearn-backend
```

### 使用 Docker Compose

在项目根目录使用：

```bash
docker-compose up backend
```

## 开发工具

### 代码格式化

```bash
# 使用 black 格式化 Python 代码
pip install black
black app/
```

### 代码检查

```bash
# 使用 flake8 进行代码检查
pip install flake8
flake8 app/
```

### 类型检查

```bash
# 使用 mypy 进行类型检查
pip install mypy
mypy app/
```

## 常见问题

### 1. 数据库连接失败

**问题**：`sqlalchemy.exc.OperationalError: unable to open database file`

**解决**：确保 `data/` 目录存在且有写入权限：

```bash
mkdir -p data
chmod 755 data
```

### 2. CORS 错误

**问题**：前端无法访问 API

**解决**：已在 `main.py` 中配置 CORS，如果仍有问题，检查 `allow_origins` 配置。

### 3. 端口被占用

**问题**：`OSError: [Errno 48] Address already in use`

**解决**：更换端口或杀死占用进程：

```bash
# 更换端口
uvicorn main:app --port 8001

# 或者杀死占用进程
lsof -ti:8000 | xargs kill -9
```

### 4. 依赖安装失败

**问题**：`pip install` 失败

**解决**：使用虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 测试

### 手动测试

访问 API 文档页面进行交互式测试：
- http://localhost:8000/docs

### 使用 curl 测试

```bash
# 健康检查
curl http://localhost:8000/health

# 获取用户列表
curl http://localhost:8000/api/users/

# 创建用户
curl -X POST http://localhost:8000/api/users/ -H "Content-Type: application/json" -d '{"nickname": "test"}'
```

## 相关文档

- [项目根 README](../../README.md)
- [Scripts 使用说明](../../scripts/README.md)
- [前端 README](../frontend/README.md)

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目仅供学习和个人使用。
