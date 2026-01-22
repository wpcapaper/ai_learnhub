"""
用户管理API路由
支持Dev模式（免注册快速体验）
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["用户管理"])


# Schemas
class UserCreateRequest(BaseModel):
    """创建用户请求"""
    nickname: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: str
    nickname: Optional[str]
    is_temp_user: bool
    user_level: Optional[str]
    total_study_time: int
    created_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    """用户统计响应"""
    total_answered: int
    correct_count: int
    accuracy: float
    mastered_count: int
    due_review_count: int


# Endpoints
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_user(
    request: UserCreateRequest,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取或创建用户（Dev模式）

    Dev模式下，如果没有提供user_id，会自动创建新用户
    """
    user = UserService.get_or_create_user(db, user_id=user_id, nickname=request.nickname)
    UserService.update_last_login(db, str(user.id))
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """列出所有用户"""
    users = UserService.list_users(db, include_deleted=include_deleted)
    return users


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: str, db: Session = Depends(get_db)):
    """获取用户学习统计"""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    stats = UserService.get_user_stats(db, user_id)
    return UserStatsResponse(**stats)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    soft_delete: bool = True,
    db: Session = Depends(get_db)
):
    """删除用户（支持软删除）"""
    success = UserService.delete_user(db, user_id, soft_delete=soft_delete)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "用户已删除"}


@router.post("/{user_id}/reset")
async def reset_user_data(user_id: str, db: Session = Depends(get_db)):
    """
    重置用户数据（Dev模式）

    删除用户的所有学习记录和批次记录
    """
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    success = UserService.reset_user_data(db, user_id)
    if not success:
        raise HTTPException(status_code=500, detail="重置失败")

    return {"message": "用户数据已重置"}
