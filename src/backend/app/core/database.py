"""
数据库配置
支持SQLite（开发）和PostgreSQL（生产）
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# 数据库连接配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/app.db"  # 默认SQLite
)

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 依赖注入
def get_db():
    """数据库会话依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
