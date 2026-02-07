"""
艾宾浩斯复习调度服务
修复SQLAlchemy 2.0兼容性
"""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import Question, UserLearningRecord, UserCourseProgress
from app.core.ebbinghaus import EbbinghausScheduler


def utcnow_with_tz():
    """获取带 UTC 时区的当前时间"""
    return datetime.now(timezone.utc)

class ReviewService:
    """艾宾浩斯复习服务（修复版）"""

    @staticmethod
    def submit_answer(
        db: Session,
        user_id: str,
        question_id: str,
        answer: str,
        is_correct: bool,
        batch_id: Optional[str] = None
    ) -> UserLearningRecord:
        """
        提交答案并更新学习记录（艾宾浩斯算法）

        变更说明：
        - 创建历史答题记录（UserAnswerHistory），保留完整历史
        - UserLearningRecord 只存储复习状态，不再存储 answer 和 is_correct
        - 错题推荐逻辑与 is_correct 解耦，只依赖 review_stage

        Args:
            db: 数据库会话
            user_id: 用户ID
            question_id: 题目ID
            answer: 用户答案
            is_correct: 是否正确
            batch_id: 关联的批次ID（可选）

        Returns:
            UserLearningRecord: 更新后的学习记录
        """
        import uuid
        from app.models import UserAnswerHistory

        # 获取当前复习阶段（用于历史记录）
        record = db.query(UserLearningRecord).filter(
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.question_id == question_id
        ).first()

        if record:
            current_stage = record.review_stage
        else:
            current_stage = 0

        # 创建历史答题记录（每次答题都创建新记录，永不更新）
        # 关键业务逻辑：保留每次答题的完整信息，追踪"历史上做错过"的题目
        history = UserAnswerHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            answer=answer,
            is_correct=is_correct,
            answered_at=datetime.utcnow(),
            review_stage=current_stage,  # 记录答题时的复习阶段
            batch_id=batch_id  # 关联批次（可选）
        )
        db.add(history)

        # 更新 UserLearningRecord（只更新复习状态字段）
        # 关键业务逻辑：is_correct、answer、answered_at 字段不再使用，避免冗余
        next_stage, next_time = EbbinghausScheduler.calculate_next_review(
            current_stage, is_correct
        )

        if record:
            # 不再更新 is_correct、answer、answered_at，只更新复习状态
            record.review_stage = next_stage
            record.next_review_time = next_time
            record.completed_in_current_round = True  # 标记在当前轮次已刷过
        else:
            # 新记录（只存储复习状态）
            record = UserLearningRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                question_id=question_id,
                review_stage=next_stage,
                next_review_time=next_time,
                completed_in_current_round=True
            )
            db.add(record)

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_next_question(
        db: Session,
        user_id: str,
        course_id: Optional[str] = None,
        batch_size: int = 10,
        allow_new_round: bool = True
    ) -> List[Question]:
        """
        获取下一批复习题目（支持多轮模式）

        优先级（修复版）：
        1. 艾宾浩斯复习阶段的题目（review_stage 在 1-7 之间，复习时间到了，且当前轮次未刷过）
        2. 当前轮次未刷过的其他题目（包括已掌握的，与复习题去重）
        3. 用户没刷过的题（新题）
        4. 如果 allow_new_round=True 且没有可用题，开始新轮

        Args:
            db: 数据库会话
            user_id: 用户ID
            course_id: 课程ID（可选）
            batch_size: 批次大小
            allow_new_round: 是否允许开始新轮（默认True）

        Returns:
            List[Question]: 题目列表
        """
        now = utcnow_with_tz()

        # 1. 优先：艾宾浩斯复习阶段的题目（按照艾宾浩斯曲线）
        # 关键业务逻辑：只看艾宾浩斯复习条件，不与轮次管理（completed_in_current_round）混合
        due_query = (
            db.query(Question)
            .join(UserLearningRecord, and_(UserLearningRecord.question_id == Question.id))
            .filter(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.next_review_time <= now,      # 复习时间到了
                UserLearningRecord.review_stage < EbbinghausScheduler.MAX_STAGE,  # 未掌握（review_stage < 8）
                UserLearningRecord.review_stage > 0,           # 有复习记录（排除新题）
                Question.is_deleted == False
            )
        )

        if course_id:
            due_query = due_query.filter(Question.course_id == course_id)

        due_questions = due_query.order_by(
            UserLearningRecord.next_review_time
        ).limit(batch_size).all()

        # 返回所有到期的题目（已与 is_correct 解耦，只依赖 review_stage）
        if len(due_questions) >= batch_size:
            return due_questions[:batch_size]

        # 2. 次优先：当前轮次未刷过的题目（与复习题去重）
        # 关键业务逻辑：只和 completed_in_current_round 有关，与 review_stage 无关
        # 轮次管理逻辑：在新轮次中，所有题目都应该可以重新刷题
        remaining_slots = batch_size - len(due_questions)

        # 获取已获取的复习题ID列表，用于去重
        due_question_ids = [q.id for q in due_questions]

        not_completed_query = (
            db.query(Question)
            .join(UserLearningRecord, and_(UserLearningRecord.question_id == Question.id))
            .filter(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.completed_in_current_round == False,  # 当前轮次未刷过（轮次管理）
                Question.is_deleted == False
            )
        )

        # 关键业务逻辑：与复习题去重，避免重复返回同一道题
        if due_question_ids:
            not_completed_query = not_completed_query.filter(~Question.id.in_(due_question_ids))

        if course_id:
            not_completed_query = not_completed_query.filter(Question.course_id == course_id)

        not_completed_questions = not_completed_query.limit(remaining_slots).all()
        result = due_questions + not_completed_questions

        if len(result) >= batch_size:
            return result[:batch_size]

        # 3. 再次：用户没刷过的题（新题）
        remaining_slots = batch_size - len(result)

        new_questions_query = (
            db.query(Question)
            .outerjoin(
                UserLearningRecord,
                and_(
                    UserLearningRecord.user_id == user_id,
                    UserLearningRecord.question_id == Question.id
                )
            )
            .filter(
                or_(
                    UserLearningRecord.id == None,  # 没有任何学习记录，完全新题
                    and_(
                        UserLearningRecord.review_stage == 0,  # 复习阶段为0，表示新题
                        UserLearningRecord.next_review_time == None  # 且没有安排复习时间
                    )
                ),
                Question.is_deleted == False
            )
        )

        if course_id:
            new_questions_query = new_questions_query.filter(Question.course_id == course_id)

        new_questions = new_questions_query.limit(remaining_slots).all()
        result = result + new_questions

        # 4. 新轮逻辑：如果没有可用题目，允许开始新轮
        # 判断条件：allow_new_round=True + 无复习题 + 无未刷题 + 无新题 + 指定了课程
        # 这意味着该课程的所有题目都已刷完且在新轮次也已刷过
        if allow_new_round and len(result) == 0 and course_id:
            from app.services.user_service import UserService

            # 开始新轮：轮次编号+1，已完轮次数+1
            # 注意：这里只更新轮次编号，不修改题目复习状态（与艾宾浩斯解耦）
            UserService.start_new_round(db, user_id, course_id)

            # 重新获取题目（不允许多次递归，防止死循环）
            result = ReviewService.get_next_question(
                db, user_id, course_id, batch_size, allow_new_round=False
            )

        return result[:batch_size]

    @staticmethod
    def get_wrong_questions(
        db: Session,
        user_id: str,
        course_id: Optional[str] = None,
        limit: int = 100
    ) -> dict:
        """
        获取用户的错题列表

        错题定义（修改版）：
        - 历史上曾经答错过（UserAnswerHistory 中存在 is_correct == False 的记录）
        - 且当前未达到已掌握状态（review_stage != 8）

        变更说明：
        - 使用 UserAnswerHistory 表查询最近的做错时间
        - 错题推荐逻辑与 is_correct 解耦，只依赖 review_stage

        Args:
            db: 数据库会话
            user_id: 用户ID
            course_id: 课程ID（可选）
            limit: 限制数量

        Returns:
            dict: {
                "questions": List[Question],  # 错题列表
                "wrong_times": {question_id: datetime}  # 最近的做错时间
            }
        """
        from sqlalchemy import func
        from app.models import UserAnswerHistory

        # 子查询：找出每个题目最近一次答错的记录（从历史记录表）
        # 关键业务逻辑：确保错题本只提取最近一次做错的情况
        latest_wrong_subquery = (
            db.query(
                UserAnswerHistory.question_id.label('q_id'),
                func.max(UserAnswerHistory.answered_at).label('wrong_time')
            )
            .filter(
                UserAnswerHistory.user_id == user_id,
                UserAnswerHistory.is_correct == False  # 只查询错题记录
            )
            .group_by(UserAnswerHistory.question_id)
            .subquery()
        )

        # 主查询：筛选出曾经答错过、且未达到已掌握状态的题目
        # 关键业务逻辑：错题本只显示历史错题且未掌握的题目
        # 即使中途答对，只要未掌握（review_stage != 8），仍在错题本中
        query = (
            db.query(Question, latest_wrong_subquery.c.wrong_time.label('wrong_time'))
            .join(
                UserLearningRecord,
                Question.id == UserLearningRecord.question_id
            )
            .join(
                latest_wrong_subquery,
                Question.id == latest_wrong_subquery.c.q_id
            )
            .filter(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.review_stage != EbbinghausScheduler.MAX_STAGE,  # 未达到已掌握（review_stage != 8）
                Question.is_deleted == False
            )
        )

        if course_id:
            query = query.filter(Question.course_id == course_id)

        results = query.limit(limit).all()

        # 分离题目和做错时间，并将 naive datetime 转换为 timezone-aware（UTC）
        questions = []
        wrong_times = {}
        for q, w_time in results:
            questions.append(q)
            # 将 naive datetime 转换为 timezone-aware（UTC）
            if w_time and w_time.tzinfo is None:
                w_time = w_time.replace(tzinfo=timezone.utc)
            wrong_times[q.id] = w_time

        return {
            "questions": questions,
            "wrong_times": wrong_times
        }

    @staticmethod
    def get_due_questions_count(db: Session, user_id: str, course_id: Optional[str] = None) -> int:
        now = utcnow_with_tz()
        query = (
            db.query(func.count(Question.id))
            .join(UserLearningRecord, and_(UserLearningRecord.question_id == Question.id))
            .filter(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.next_review_time <= now,
                Question.is_deleted == False
            )
        )

        if course_id:
            query = query.filter(Question.course_id == course_id)

        return query.scalar() or 0

    @staticmethod
    def get_review_queue(db: Session, user_id: str, limit: int = 100):
        now = utcnow_with_tz()

        query = (
            db.query(Question, UserLearningRecord)
            .join(UserLearningRecord, and_(UserLearningRecord.question_id == Question.id))
            .filter(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.next_review_time <= now,
                UserLearningRecord.review_stage < EbbinghausScheduler.MAX_STAGE,
                Question.is_deleted == False
            )
            .order_by(UserLearningRecord.next_review_time)
            .limit(limit)
        )

        return query.all()

    @staticmethod
    def get_mastered_questions(
        db: Session,
        user_id: str,
        course_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Question]:
        """获取已掌握的题目"""
        query = (
            db.query(Question)
            .join(UserLearningRecord, and_(UserLearningRecord.question_id == Question.id))
            .filter(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.review_stage == EbbinghausScheduler.MAX_STAGE,
                Question.is_deleted == False
            )
        )

        if course_id:
            query = query.filter(Question.course_id == course_id)

        questions = query.all()
        return questions[:limit]

        if course_id:
            query = query.filter(Question.course_id == course_id)

        questions = query.all()
        return questions[:limit]
