FROM python:3.11-slim

WORKDIR /app

# 大包下载超时设置（scikit-learn、torch 等体积大，默认 30s 易超时）
ENV UV_HTTP_TIMEOUT=600 UV_FETCH_RETRIES=5

# 安装 uv 以加快依赖安装
COPY pyproject.toml uv.lock* ./
RUN pip install uv && uv sync --no-dev --no-install-project

# 安装项目自身
COPY . .
RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
