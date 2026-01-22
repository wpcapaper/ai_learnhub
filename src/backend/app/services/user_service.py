"""
用户管理模块
支持Dev模式（免注册快速体验）和生产模式
"""
import uuid
import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import User, UserCourseProgress


class UserService:
    """用户服务"""

    @staticmethod
    def _generate_user_id_from_nickname(nickname: str) -> str:
        """
        根据昵称生成确定性的用户ID

        使用SHA256哈希确保同一个昵称总是生成相同的ID

        Args:
            nickname: 昵称

        Returns:
            str: 确定性的用户ID
        """
        hash_bytes = hashlib.sha256(nickname.encode('utf-8')).digest()
        return str(uuid.UUID(bytes=hash_bytes[:16]))

    @staticmethod
    def get_or_create_user(db: Session, user_id: Optional[str] = None, nickname: Optional[str] = None) -> User:
        """
        获取或创建用户（Dev模式）

        Dev模式下：
        - 如果提供user_id，尝试获取现有用户
        - 如果提供nickname，基于nickname生成确定性ID并查找或创建
        - 如果都没提供，创建随机ID的新用户

        Args:
            db: 数据库会话
            user_id: 用户ID（可选）
            nickname: 昵称（可选，Dev模式下默认生成）

        Returns:
            User: 用户对象
        """
        if user_id:
            # 尝试获取现有用户
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user

        # 如果提供了nickname，使用确定性ID
        if nickname:
            deterministic_id = UserService._generate_user_id_from_nickname(nickname)
            user = db.query(User).filter(User.id == deterministic_id).first()
            if user:
                return user

            # 创建新用户（基于nickname的确定性ID）
            user = User(
                id=deterministic_id,
                username=f"dev_{deterministic_id[:8]}",
                email=f"dev_{deterministic_id[:8]}@local.dev",
                password_hash="dev_mode_no_password",
                nickname=nickname,
                is_temp_user=True,
                user_level="beginner",
                created_at=datetime.utcnow()
            )
        else:
            # 创建新用户（随机ID）
            user = User(
                id=str(uuid.uuid4()),
                username=f"dev_{uuid.uuid4().hex[:8]}",
                email=f"dev_{uuid.uuid4().hex[:8]}@local.dev",
                password_hash="dev_mode_no_password",
                nickname=f"学员{uuid.uuid4().hex[:6]}",
                is_temp_user=True,
                user_level="beginner",
                created_at=datetime.utcnow()
            )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: str) -> Optional[User]:
        """
        获取用户

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Optional[User]: 用户对象或None
        """
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_last_login(db: Session, user_id: str):
        """
        更新用户最后登录时间

        Args:
            db: 数据库会话
            user_id: 用户ID
        """
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = datetime.utcnow()
            db.commit()

    @staticmethod
    def list_users(db: Session, include_deleted: bool = False) -> list[User]:
        """
        列出所有用户

        Args:
            db: 数据库会话
            include_deleted: 是否包含已删除用户

        Returns:
            list[User]: 用户列表
        """
        query = db.query(User)
        if not include_deleted:
            query = query.filter(User.is_deleted == False)
        return query.order_by(User.created_at.desc()).all()

    @staticmethod
    def delete_user(db: Session, user_id: str, soft_delete: bool = True) -> bool:
        """
        删除用户

        Args:
            db: 数据库会话
            user_id: 用户ID
            soft_delete: 是否软删除（Dev模式建议软删除）

        Returns:
            bool: 是否成功删除
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        if soft_delete:
            user.is_deleted = True
        else:
            db.delete(user)
        db.commit()
        return True

    @staticmethod
    def reset_user_data(db: Session, user_id: str) -> bool:
        """
        重置用户数据（Dev模式）

        删除用户的所有学习记录和批次记录

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            bool: 是否成功重置
        """
        from app.models import UserLearningRecord, QuizBatch, BatchAnswer

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # 删除批次答题记录
        batch_ids = db.query(QuizBatch.id).filter(QuizBatch.user_id == user_id).all()
        if batch_ids:
            batch_id_list = [bid[0] for bid in batch_ids]
            db.query(BatchAnswer).filter(BatchAnswer.batch_id.in_(batch_id_list)).delete(synchronize_session=False)

        # 删除批次记录
        db.query(QuizBatch).filter(QuizBatch.user_id == user_id).delete(synchronize_session=False)

        # 删除学习记录
        db.query(UserLearningRecord).filter(UserLearningRecord.user_id == user_id).delete(synchronize_session=False)

        db.commit()
        return True

    @staticmethod
    def get_user_stats(db: Session, user_id: str) -> dict:
        """
        获取用户学习统计

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            dict: 用户统计数据
        """
        from app.models import UserLearningRecord
        from sqlalchemy import func

        # 基础统计
        total_records = db.query(func.count(UserLearningRecord.id)).filter(
            UserLearningRecord.user_id == user_id
        ).scalar() or 0

        correct_records = db.query(func.count(UserLearningRecord.id)).filter(
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.is_correct == True
        ).scalar() or 0

        # 已掌握的题目（review_stage = 8）
        mastered_records = db.query(func.count(UserLearningRecord.id)).filter(
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.review_stage == 8
        ).scalar() or 0

        # 待复习题目
        from datetime import datetime
        due_records = db.query(func.count(UserLearningRecord.id)).filter(
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.next_review_time <= datetime.utcnow()
        ).scalar() or 0

        return {
            "total_answered": total_records,
            "correct_count": correct_records,
            "accuracy": round(correct_records / total_records * 100, 2) if total_records > 0 else 0,
            "mastered_count": mastered_records,
            "due_review_count": due_records,
        }

    @staticmethod
    def get_or_create_progress(
        db: Session,
        user_id: str,
        course_id: str
    ) -> UserCourseProgress:
        """
        获取或创建用户课程进度记录

        轮次管理：
        - 跟踪用户在每个课程上的刷题轮次
        - 新用户从第1轮开始
        - 每次完成所有题目后自动进入下一轮

        Args:
            db: 数据库会话
            user_id: 用户ID
            course_id: 课程ID

        Returns:
            UserCourseProgress: 用户课程进度对象
        """
        progress = db.query(UserCourseProgress).filter(
            UserCourseProgress.user_id == user_id,
            UserCourseProgress.course_id == course_id
        ).first()

        if not progress:
            progress = UserCourseProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                current_round=1,
                total_rounds_completed=0,
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)

        return progress

    @staticmethod
    def start_new_round(
        db: Session,
        user_id: str,
        course_id: str
    ) -> UserCourseProgress:
        """
        开始新的一轮刷题（轮次管理核心逻辑 - 修复版）

        轮次管理与艾宾浩斯复习算法解耦：
        - current_round += 1  # 进入下一轮，仅用于统计和展示
        - total_rounds_completed += 1  # 记录已完成的轮次数
        - 更新 updated_at 时间戳  # 记录轮次切换时间
        - 重置 completed_in_current_round = False，让题目可以重新在新轮次刷题

        Args:
            db: 数据库会话
            user_id: 用户ID
            course_id: 课程ID

        Returns:
            UserCourseProgress: 更新后的用户课程进度对象
        """
        import uuid
        from app.models import Question, UserLearningRecord

        progress = UserService.get_or_create_progress(db, user_id, course_id)

        # 进入新轮：轮次编号+1，记录用户已完成一轮完整刷题
        progress.current_round += 1
        progress.total_rounds_completed += 1
        progress.updated_at = datetime.utcnow()

        # 修复：重置所有题目的 completed_in_current_round = False
        # 查询该课程下该用户的所有学习记录
        all_records = db.query(UserLearningRecord).join(
            Question, Question.id == UserLearningRecord.question_id
        ).filter(
            UserLearningRecord.user_id == user_id,
            Question.course_id == course_id
        ).all()

        # 将所有题目的轮次标记重置为False
        for record in all_records:
            record.completed_in_current_round = False

        db.commit()
        db.refresh(progress)

        return progress

    @staticmethod
    def get_course_progress(
        db: Session,
        user_id: str,
        course_id: str
    ) -> Optional[UserCourseProgress]:
        """
        获取用户课程进度（不自动创建）

        Args:
            db: 数据库会话
            user_id: 用户ID
            course_id: 课程ID

        Returns:
            Optional[UserCourseProgress]: 用户课程进度对象，如果不存在则返回None
        """
        return db.query(UserCourseProgress).filter(
            UserCourseProgress.user_id == user_id,
            UserCourseProgress.course_id == course_id
        ).first()
