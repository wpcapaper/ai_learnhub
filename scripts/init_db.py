#!/usr/bin/env python3
"""
数据库初始化脚本
创建所有数据库表
"""
import sys
import os
from pathlib import Path

# Add src/backend to path
backend_dir = Path(__file__).parent / ".." / "src" / "backend"
sys.path.insert(0, str(backend_dir))

# Change to backend directory so relative paths work
os.chdir(str(backend_dir))

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

from app.models import init_db

if __name__ == "__main__":
    print("初始化数据库...")
    init_db()
    print("完成！")
