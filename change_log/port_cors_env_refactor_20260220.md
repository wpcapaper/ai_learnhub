# 端口优化 + CORS 修复 + 环境变量重构

**日期**: 2026-02-20  
**类型**: 重构 / 安全修复

---

## 变更概述

1. **端口规划优化** - 分离各服务端口，避免混淆
2. **CORS 安全修复** - 从 `allow_origins=["*"]` 改为环境变量配置
3. **环境变量统一** - 删除冗余的子目录 `.env.example`，统一到根目录

---

## 1. 端口规划

### 新端口方案

| 服务 | 旧端口 | 新端口 | 说明 |
|------|--------|--------|------|
| Backend API | 8000 | **8000** | 保持不变 |
| Frontend (C端) | 3000 | **3000** | 保持不变 |
| Admin Frontend | 3002 | **8080** | 独立区间 |
| Langfuse | 3001 | **9090** | 独立区间 |
| Redis | 6379 | 6379 | 标准端口 |
| PostgreSQL | 5432 | 5432 | 标准端口 |

### 端口规划原则

```
┌─────────────────────────────────────────────────────────┐
│  端口区间        │ 用途                                 │
├─────────────────────────────────────────────────────────┤
│  3000           │ C端前端 (用户端)                     │
│  8000           │ 后端 API                             │
│  8080           │ 管理端前端                           │
│  9090           │ 监控平台 (Langfuse)                  │
│  6379           │ Redis (基础设施)                     │
│  5432           │ PostgreSQL (基础设施)                │
└─────────────────────────────────────────────────────────┘
```

---

## 2. CORS 安全修复

### 问题描述

原代码允许任何源访问 API，存在 CSRF 攻击风险：

```python
# 旧代码 (不安全)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```

### 修复方案

从环境变量读取允许的源：

```python
# 新代码 (安全)
def _get_allowed_origins() -> list[str]:
    origins_str = os.getenv("ALLOWED_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",") if o.strip()]
    return [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    ...
)
```

### 配置方式

```bash
# .env 文件
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# 生产环境
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

---

## 3. 环境变量统一

### 变更前

```
aie55_llm5_learnhub/
├── .env.example                          # 根目录配置
├── src/
│   ├── backend/.env.example              # 冗余！与根目录 90% 重复
│   ├── frontend/.env.example             # 冗余！Docker 已注入
│   └── admin-frontend/.env.example       # 冗余！Docker 已注入
```

### 变更后

```
aie55_llm5_learnhub/
├── .env              # 实际配置 (git ignored)
└── .env.example      # 唯一的配置模板
```

### 删除的文件

| 文件 | 删除原因 |
|------|----------|
| `src/backend/.env.example` | 与根目录重复，Docker 用根目录 `.env` |
| `src/frontend/.env.example` | Docker 通过 `docker-compose.yml` 注入，本地开发用代码默认值 |
| `src/admin-frontend/.env.example` | 同上 |

### 各环境配置来源

| 环境 | 配置来源 |
|------|----------|
| **Docker** | 根目录 `.env` → `docker-compose.yml` 注入各服务 |
| **后端本地开发** | 根目录 `.env`（`load_dotenv()` 向上查找） |
| **前端本地开发** | 代码默认值 `\|\| 'http://localhost:8000'` |

---

## 4. 修改的文件

### 新建

| 文件 | 说明 |
|------|------|
| `.env.example` | 统一的环境变量配置模板 |

### 修改

| 文件 | 变更 |
|------|------|
| `docker-compose.yml` | 使用 `${VAR:-default}` 环境变量语法 |
| `src/backend/main.py` | 添加 `_get_allowed_origins()` 函数 |
| `RAG_MANUAL.md` | 更新端口表格 |
| `README.md` | 添加端口配置说明 |

### 删除

| 文件 | 说明 |
|------|------|
| `src/backend/.env.example` | 冗余 |
| `src/frontend/.env.example` | 冗余 |
| `src/admin-frontend/.env.example` | 冗余 |

---

## 5. docker-compose.yml 关键变更

```yaml
services:
  backend:
    env_file:
      - .env    # 读取根目录 .env
    environment:
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:3000,http://localhost:8080}
    ports:
      - "${BACKEND_PORT:-8000}:8000"

  frontend:
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT:-8000}
    ports:
      - "${FRONTEND_PORT:-3000}:3000"

  admin-frontend:
    environment:
      - NEXT_PUBLIC_ADMIN_API_URL=http://localhost:${BACKEND_PORT:-8000}
    ports:
      - "${ADMIN_FRONTEND_PORT:-8080}:3000"

  langfuse:
    ports:
      - "${LANGFUSE_PORT:-9090}:3000"
    environment:
      - NEXTAUTH_URL=http://localhost:${LANGFUSE_PORT:-9090}
```

---

## 6. 迁移指南

### 从旧配置迁移

1. **删除旧的 .env 文件**（如果存在于子目录）：
   ```bash
   rm src/backend/.env src/frontend/.env.local src/admin-frontend/.env.local
   ```

2. **创建根目录 .env**：
   ```bash
   cp .env.example .env
   ```

3. **编辑 .env 填入实际值**：
   ```bash
   vim .env
   # 填入 LLM_API_KEY、RAG_OPENAI_API_KEY 等
   ```

4. **重启服务**：
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### 访问地址变更

| 服务 | 旧地址 | 新地址 |
|------|--------|--------|
| Admin 管理端 | http://localhost:3002 | **http://localhost:8080** |
| Langfuse 监控 | http://localhost:3001 | **http://localhost:9090** |

---

## 7. 测试验证

```bash
# 验证后端启动
cd src/backend && python -c "from main import app; print('OK')"

# 验证 CORS 配置
curl -I -X OPTIONS http://localhost:8000/api/users \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"

# 验证 Docker 配置
docker-compose config
```

---

## 8. 相关 Issue/PR

- Code Review: `change_log/code_review_admin_security_fix_20260220.md`
