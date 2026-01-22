"""
批次刷题服务（修改版 - 支持course_id）
实现批次刷题和统一对答案
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import QuizBatch, BatchAnswer, Question
from app.services.review_service import ReviewService
from app.services.user_service import UserService


class QuizService:
    """批次刷题服务（修改版 - 支持course_id）"""

    @staticmethod
    def start_batch(
        db: Session,
        user_id: str,
        mode: str = "practice",
        batch_size: int = 10,
        course_id: str = None
    ) -> QuizBatch:
        """
        开始一个新的刷题批次（支持轮次跟踪）

        新增功能：
        - 记录批次所属轮次
        - 支持多轮刷题

        Args:
            db: 数据库会话
            user_id: 用户ID
            mode: 模式
            batch_size: 批次大小
            course_id: 课程ID（必需）

        Returns:
            QuizBatch: 批次对象
        """
        if not course_id:
            raise ValueError("course_id is required")

        # 获取用户课程进度
        progress = UserService.get_or_create_progress(db, user_id, course_id)

        # 获取题目（支持开始新轮）
        # allow_new_round=True 确保当所有题目都已刷完时，能自动开启新轮
        # 这是轮次管理的核心触发点
        questions = ReviewService.get_next_question(
            db, user_id, course_id, batch_size, allow_new_round=True
        )

        if not questions:
            raise ValueError("没有可用的题目")

        # 创建批次（包含轮次信息）
        import uuid
        batch = QuizBatch(
            id=str(uuid.uuid4()),
            user_id=user_id,
            batch_size=len(questions),
            mode=mode,
            round_number=progress.current_round,  # 记录当前轮次，便于统计和追溯
            started_at=datetime.utcnow(),
            status="in_progress"
        )
        db.add(batch)
        db.flush()

        # 创建批次答题记录
        for question in questions:
            answer = BatchAnswer(
                id=str(uuid.uuid4()),
                batch_id=batch.id,
                question_id=question.id,
                user_answer=None,
                is_correct=None,
                answered_at=None
            )
            db.add(answer)

        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def submit_batch_answer(
        db: Session,
        user_id: str,
        batch_id: str,
        question_id: str,
        answer: str
    ) -> BatchAnswer:
        """
        提交批次中的单题答案（批次进行中）

        Args:
            db: 数据库会话
            user_id: 用户ID
            batch_id: 批次ID
            question_id: 题目ID
            answer: 用户答案

        Returns:
            BatchAnswer: 答题记录
        """
        # 验证批次归属
        batch = db.query(QuizBatch).filter(
            QuizBatch.id == batch_id,
            QuizBatch.user_id == user_id,
            QuizBatch.status == "in_progress"
        ).first()

        if not batch:
            raise ValueError("批次不存在或已完成")

        # 更新答案
        answer_record = db.query(BatchAnswer).filter(
            BatchAnswer.batch_id == batch_id,
            BatchAnswer.question_id == question_id
        ).first()

        if not answer_record:
            raise ValueError("答题记录不存在")

        answer_record.user_answer = answer
        answer_record.answered_at = datetime.utcnow()

        db.commit()
        db.refresh(answer_record)
        return answer_record

    @staticmethod
    def finish_batch(
        db: Session,
        user_id: str,
        batch_id: str
    ) -> dict:
        """
        完成批次（统一对答案）

        Args:
            db: 数据库会话
            user_id: 用户ID
            batch_id: 批次ID

        Returns:
            dict: 批次结果统计
        """
        # 验证批次
        batch = db.query(QuizBatch).filter(
            QuizBatch.id == batch_id,
            QuizBatch.user_id == user_id,
            QuizBatch.status == "in_progress"
        ).first()

        if not batch:
            raise ValueError("批次不存在或已完成")

        # 获取所有答题记录
        answers = db.query(BatchAnswer).filter(
            BatchAnswer.batch_id == batch_id
        ).all()

        # 获取题目用于判断正确性
        question_ids = [a.question_id for a in answers]
        questions = {
            q.id: q
            for q in db.query(Question).filter(Question.id.in_(question_ids)).all()
        }

        # 统一计算对错
        total = len(answers)
        correct = 0
        wrong = 0

        for answer in answers:
            question = questions.get(answer.question_id)
            if question and answer.user_answer:
                answer.is_correct = (answer.user_answer == question.correct_answer)

                if answer.is_correct:
                    correct += 1
                else:
                    wrong += 1

        # 更新批次状态
        batch.status = "completed"
        batch.completed_at = datetime.utcnow()

        db.commit()

        # 保存到学习记录（传递 batch_id 以关联历史记录）
        for answer in answers:
            if answer.user_answer:
                ReviewService.submit_answer(
                    db,
                    user_id=user_id,
                    question_id=answer.question_id,
                    answer=answer.user_answer,
                    is_correct=answer.is_correct,
                    batch_id=batch_id  # 关联批次
                )

        return {
            "batch_id": batch_id,
            "total": total,
            "correct": correct,
            "wrong": wrong,
            "accuracy": round(correct / total * 100, 2) if total > 0 else 0
        }

    @staticmethod
    def get_batch_questions(
        db: Session,
        user_id: str,
        batch_id: str
    ) -> List[dict]:
        """
        获取批次中的题目和答题状态

        Args:
            db: 数据库会话
            user_id: 用户ID
            batch_id: 批次ID

        Returns:
            List[dict]: 题目列表
        """
        batch = db.query(QuizBatch).filter(
            QuizBatch.id == batch_id,
            QuizBatch.user_id == user_id
        ).first()

        if not batch:
            raise ValueError("批次不存在")

        # 获取答题记录
        answers = db.query(BatchAnswer).filter(
            BatchAnswer.batch_id == batch_id
        ).all()

        question_ids = [a.question_id for a in answers]
        questions = {
            q.id: q
            for q in db.query(Question).filter(Question.id.in_(question_ids)).all()
        }

        # 获取题集信息（用于标注题目来源）
        from app.models import QuestionSet
        question_set_codes = {}  # 题目ID -> 所属固定题集名称列表
        # 无论批次状态如何，都返回题集来源，让用户在答题过程中也能看到
        # 从questions中获取所有涉及的课程ID
        course_ids = list(set(q.course_id for q in questions.values() if q.course_id))
        all_question_sets = db.query(QuestionSet).filter(QuestionSet.course_id.in_(course_ids)).all()
        for qs in all_question_sets:
            if qs.fixed_question_ids:
                for qid in qs.fixed_question_ids:
                    if qid not in question_set_codes:
                        question_set_codes[qid] = []
                    question_set_codes[qid].append(qs.name)  # 返回题集名称而非code

        result = []
        for answer in answers:
            question = questions.get(answer.question_id)
            if question:
                show_correct = (batch.status == "completed")

                result.append({
                    "id": question.id,
                    "content": question.content,
                    "question_type": question.question_type,
                    "options": question.options,
                    "correct_answer": question.correct_answer if show_correct else None,
                    "explanation": question.explanation if show_correct else None,
                    "user_answer": answer.user_answer,
                    "is_correct": answer.is_correct if show_correct else None,
                    "answered_at": answer.answered_at.isoformat() if answer.answered_at else None,
                    "question_set_codes": question_set_codes.get(question.id, [])  # 始终返回题集来源
                })

        return result

    @staticmethod
    def list_batches(
        db: Session,
        user_id: str,
        limit: int = 50
    ) -> List[QuizBatch]:
        """
        列出用户的所有批次

        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 限制数量

        Returns:
            List[QuizBatch]: 批次列表
        """
        batches = db.query(QuizBatch).filter(
            QuizBatch.user_id == user_id,
            QuizBatch.is_deleted == False
        ).order_by(
            QuizBatch.started_at.desc()
        ).limit(limit).all()

        return batches
