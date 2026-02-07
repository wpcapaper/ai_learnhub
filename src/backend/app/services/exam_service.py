"""
考试模式服务（修改版 - 支持course_id和双模式）
实现固定题集和规则抽取考试
"""
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from app.models import Question, QuizBatch, BatchAnswer, Course
from app.services.quiz_service import QuizService
from app.services import QuestionSetService, UserSettingsService

class ExamService:
    """考试模式服务（修改版）"""

    @staticmethod
    def start_exam(
        db: Session,
        user_id: str,
        course_id: str,  # ✅ 新增必需参数
        exam_mode: str = "extraction",  # "extraction" | "fixed_set"
        question_type_config: Optional[Dict[str, int]] = None,
        difficulty_range: Optional[List[int]] = None,
        question_set_code: Optional[str] = None
    ) -> QuizBatch:
        """
        开始一次考试（修改版 - 支持轮次管理）

        支持两种模式：
        1. extraction: 动态抽取题目（按题型数量）
        2. fixed_set: 使用固定题集

        配置优先级：请求参数 > 用户设置 > 课程默认 > 硬编码

        轮次管理逻辑（修复版）：
        - 在开始考试前，通过获取1个题来触发轮次检查
        - 如果题库中所有题目都已刷完（无可用题），会自动开启新轮
        - 这样确保考试模式与刷题模式的轮次管理逻辑一致

        Args:
            db: 数据库会话
            user_id: 用户ID
            course_id: 课程ID（必需）
            exam_mode: 考试模式（"extraction" | "fixed_set"）
            question_type_config: 题型配置（如 {"single_choice": 30}）
            difficulty_range: 难度范围 [1,5]
            question_set_code: 固定题集代码（fixed_set模式必需）

        Returns:
            QuizBatch: 考试批次对象
        """
        import uuid

        if not course_id:
            raise ValueError("course_id is required")

        # 轮次管理：在开始考试前检查是否需要开启新轮
        # 通过获取1个题来触发 ReviewService.get_next_question 的 allow_new_round 逻辑
        # 如果题库中所有题目都已刷完（无可用题），会自动开启新轮
        # 这样确保考试模式与刷题模式的轮次管理逻辑一致
        try:
            from app.services.review_service import ReviewService
            test_questions = ReviewService.get_next_question(
                db, user_id, course_id, 1, allow_new_round=True
            )
            # 获取到题目后立即释放，不影响后续考试流程
        except Exception:
            # 如果获取失败（如没有题目），继续执行，后续会抛出更具体的错误
            pass

        if exam_mode == "extraction":
            # 模式1：动态抽取

            # 获取配置（优先级：请求参数 > 用户设置 > 课程默认 > 硬编码）
            if question_type_config:
                config = {
                    "question_type_config": question_type_config,
                    "difficulty_range": difficulty_range or [1,5]
                }
            else:
                config = UserSettingsService.get_exam_config(db, user_id, course_id)

            # 验证题型数量
            validation = QuestionSetService.validate_question_type_availability(
                db, course_id, config["question_type_config"]
            )
            if not validation["valid"]:
                raise ValueError(", ".join(validation["errors"]))

            # 按题型抽取题目
            questions = []
            for q_type, count in config["question_type_config"].items():
                query = db.query(Question).filter(
                    Question.course_id == course_id,
                    Question.question_type == q_type,
                    Question.is_deleted == False
                )

                if config.get("difficulty_range"):
                    min_diff, max_diff = config["difficulty_range"]
                    query = query.filter(
                        Question.difficulty >= min_diff,
                        Question.difficulty <= max_diff
                    )

                available = query.all()
                if available:
                    import random
                    questions.extend(random.sample(available, min(count, len(available))))

        elif exam_mode == "fixed_set":
            # 模式2：固定题集
            if not question_set_code:
                raise ValueError("question_set_code is required for fixed_set mode")

            question_set = QuestionSetService.get_question_set_by_code(
                db, question_set_code
            )

            if not question_set:
                raise ValueError(f"Question set not found: {question_set_code}")

            # 验证题集属于该课程
            if question_set.course_id != course_id:
                raise ValueError(f"Question set {question_set_code} does not belong to course {course_id}")

            question_ids = question_set.fixed_question_ids
            questions = db.query(Question).filter(
                Question.id.in_(question_ids),
                Question.is_deleted == False
            ).all()
        else:
            raise ValueError(f"Invalid exam_mode: {exam_mode}. Must be 'extraction' or 'fixed_set'")

        if not questions:
            raise ValueError("没有可用的考试题目")

        # 创建考试批次
        batch = QuizBatch(
            id=str(uuid.uuid4()),
            user_id=user_id,
            batch_size=len(questions),
            mode="exam",
            started_at=datetime.utcnow(),
            status="in_progress"
        )
        db.add(batch)
        db.flush()

        # 创建答题记录
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
    def submit_exam_answer(
        db: Session,
        user_id: str,
        batch_id: str,
        question_id: str,
        answer: str
    ) -> BatchAnswer:
        """
        提交考试中的单题答案（考试进行中，不判断对错）

        Args:
            db: 数据库会话
            user_id: 用户ID
            batch_id: 考试批次ID
            question_id: 题目ID
            answer: 用户答案

        Returns:
            BatchAnswer: 答题记录
        """
        # 验证考试批次
        batch = db.query(QuizBatch).filter(
            QuizBatch.id == batch_id,
            QuizBatch.user_id == user_id,
            QuizBatch.mode == "exam",
            QuizBatch.status == "in_progress"
        ).first()

        if not batch:
            raise ValueError("考试批次不存在或已完成")

        # 更新答案（考试模式不判断对错）
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
    def finish_exam(
        db: Session,
        user_id: str,
        batch_id: str
    ) -> dict:
        """
        完成考试（统一计算成绩）

        Args:
            db: 数据库会话
            user_id: 用户ID
            batch_id: 考试批次ID

        Returns:
            dict: 考试结果
        """
        # 验证考试批次
        batch = db.query(QuizBatch).filter(
            QuizBatch.id == batch_id,
            QuizBatch.user_id == user_id,
            QuizBatch.mode == "exam",
            QuizBatch.status == "in_progress"
        ).first()

        if not batch:
            raise ValueError("考试批次不存在或已完成")

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

        # 统一计算对错（考试模式只在完成时计算）
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

        # 更新考试状态
        batch.status = "completed"
        batch.completed_at = datetime.utcnow()

        db.commit()

        # 保存到学习记录（传递 batch_id 以关联历史记录）
        from app.services.review_service import ReviewService
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
            "score": round(correct / total * 100, 2) if total > 0 else 0
        }

    @staticmethod
    def get_exam_questions(
        db: Session,
        user_id: str,
        batch_id: str,
        show_answers: bool = False
    ) -> List[dict]:
        """
        获取考试中的题目

        考试进行中：不显示正确答案和解析
        考试完成：显示正确答案和解析

        Args:
            db: 数据库会话
            user_id: 用户ID
            batch_id: 考试批次ID
            show_answers: 是否显示答案（默认根据考试状态判断）

        Returns:
            List[dict]: 题目列表
        """
        batch = db.query(QuizBatch).filter(
            QuizBatch.id == batch_id,
            QuizBatch.user_id == user_id,
            QuizBatch.mode == "exam"
        ).first()

        if not batch:
            raise ValueError("考试批次不存在")

        # 获取答题记录
        answers = db.query(BatchAnswer).filter(
            BatchAnswer.batch_id == batch_id
        ).all()

        question_ids = [a.question_id for a in answers]
        questions = {
            q.id: q
            for q in db.query(Question).filter(Question.id.in_(question_ids)).all()
        }

        # 根据考试状态决定是否显示答案
        show_correct = show_answers or (batch.status == "completed")

        # 获取题集信息（用于标注题目来源）
        from app.models import QuestionSet
        question_set_codes = {}  # 题目ID -> 所属固定题集名称列表
        # 无论考试状态如何，都返回题集来源，让用户在答题过程中也能看到
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
