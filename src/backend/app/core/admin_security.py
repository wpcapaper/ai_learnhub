"""
Admin API 安全模块

提供 IP 白名单认证和路径验证等安全功能。
"""

import os
import re
from typing import List, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# 默认白名单：本地开发环境
DEFAULT_ALLOWED_IPS = [
    "127.0.0.1",
    "::1",
    "localhost",
]


def get_allowed_ips() -> List[str]:
    """
    获取允许访问 Admin API 的 IP 白名单
    
    优先从环境变量 ADMIN_ALLOWED_IPS 读取，多个 IP 用逗号分隔。
    未设置时使用默认的本地开发白名单。
    """
    env_ips = os.getenv("ADMIN_ALLOWED_IPS", "")
    if env_ips:
        # 支持逗号分隔的 IP 列表
        ips = [ip.strip() for ip in env_ips.split(",") if ip.strip()]
        return ips
    return DEFAULT_ALLOWED_IPS


def validate_id_path(id_value: str, id_name: str = "ID") -> str:
    """
    验证路径参数中的 ID，防止路径穿越攻击
    
    Args:
        id_value: 要验证的 ID 值
        id_name: ID 参数名称（用于错误消息）
    
    Returns:
        清理后的 ID 值
    
    Raises:
        HTTPException: 如果 ID 包含非法字符
    """
    if not id_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{id_name} 不能为空"
        )
    
    # 检查路径穿越模式
    dangerous_patterns = [
        "..",           # 路径穿越
        "/",            # 路径分隔符
        "\\",           # Windows 路径分隔符
        "\x00",         # NULL 字节
    ]
    
    for pattern in dangerous_patterns:
        if pattern in id_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的 {id_name}：包含非法字符"
            )
    
    # 只允许安全字符：字母、数字、下划线、连字符
    if not re.match(r'^[a-zA-Z0-9_\-]+$', id_value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的 {id_name}：只允许字母、数字、下划线和连字符"
        )
    
    return id_value


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP 地址
    
    优先检查代理头，然后回退到直接连接 IP。
    """
    # 检查 X-Forwarded-For 头（代理场景）
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 取第一个 IP（最原始的客户端 IP）
        return forwarded.split(",")[0].strip()
    
    # 检查 X-Real-IP 头（Nginx 等代理）
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 回退到直接连接的客户端地址
    if request.client:
        return request.client.host
    
    return "unknown"


class AdminIPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Admin API IP 白名单中间件
    
    只允许白名单中的 IP 访问 /api/admin/* 路由。
    其他路由不受影响。
    
    使用方式：
        from app.core.admin_security import AdminIPWhitelistMiddleware
        app.add_middleware(AdminIPWhitelistMiddleware)
    
    环境变量：
        ADMIN_ALLOWED_IPS: 逗号分隔的 IP 白名单（可选）
    """
    
    def __init__(self, app, admin_prefix: str = "/api/admin"):
        super().__init__(app)
        self.admin_prefix = admin_prefix
        self._allowed_ips: Optional[List[str]] = None
    
    @property
    def allowed_ips(self) -> List[str]:
        """延迟加载 IP 白名单"""
        if self._allowed_ips is None:
            self._allowed_ips = get_allowed_ips()
        return self._allowed_ips
    
    async def dispatch(self, request: Request, call_next):
        # 只对 Admin API 路径进行白名单检查
        if not request.url.path.startswith(self.admin_prefix):
            return await call_next(request)
        
        client_ip = get_client_ip(request)
        
        # 开发模式：允许所有 IP（白名单包含 "*"）
        if "*" in self.allowed_ips:
            return await call_next(request)
        
        # 检查 IP 是否在白名单中
        if client_ip not in self.allowed_ips:
            # 额外检查：localhost 可能有不同的表示形式
            localhost_aliases = ["127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"]
            normalized_client_ip = client_ip.lower()
            
            is_localhost = any(
                alias in normalized_client_ip or normalized_client_ip in alias
                for alias in localhost_aliases
            )
            
            if not is_localhost:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "访问被拒绝：IP 不在白名单中",
                        "client_ip": client_ip
                    }
                )
        
        return await call_next(request)


# 便捷函数：验证课程 ID
def validate_course_id(course_id: str) -> str:
    """验证课程 ID"""
    return validate_id_path(course_id, "课程 ID")


# 便捷函数：验证章节 ID
def validate_chapter_id(chapter_id: str) -> str:
    """验证章节 ID"""
    return validate_id_path(chapter_id, "章节 ID")
