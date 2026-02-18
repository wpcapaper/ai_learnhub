FROM python:3.11-slim

WORKDIR /app

# 安装 uv 加速依赖安装
COPY pyproject.toml uv.lock* ./
RUN pip install uv && uv sync --no-dev --no-install-project

# 安装项目
COPY . .
RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
