"""
题集服务
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Course, QuestionSet, Question


class QuestionSetService:
    """题集服务"""

    @staticmethod
    def get_question_sets(db: Session, course_id: str, active_only: bool = True) -> List[QuestionSet]:
        """
        获取课程的题集列表

        Args:
            db: 数据库会话
            course_id: 课程ID
            active_only: 是否只返回启用的题集

        Returns:
            List[QuestionSet]: 题集列表
        """
        query = db.query(QuestionSet).filter(
            QuestionSet.course_id == course_id,
            QuestionSet.is_deleted == False
        )

        if active_only:
            query = query.filter(QuestionSet.is_active == True)

        question_sets = query.order_by(QuestionSet.created_at.desc()).all()
        return question_sets

    @staticmethod
    def get_question_set_by_code(db: Session, set_code: str) -> Optional[QuestionSet]:
        """
        根据代码获取题集

        Args:
            db: 数据库会话
            set_code: 题集代码

        Returns:
            Optional[QuestionSet]: 题集对象
        """
        question_set = db.query(QuestionSet).filter(
            QuestionSet.code == set_code,
            QuestionSet.is_deleted == False
        ).first()

        return question_set

    @staticmethod
    def validate_question_type_availability(
        db: Session,
        course_id: str,
        question_type_config: Dict[str, int]
    ) -> Dict[str, any]:
        """
        验证题型数量是否可用

        Args:
            db: 数据库会话
            course_id: 课程ID
            question_type_config: 题型配置，如 {"single_choice": 30, "multiple_choice": 10}

        Returns:
            Dict: {"valid": bool, "errors": List[str], "available": Dict[str, int]}
        """
        # 查询各题型的可用数量
        available_counts = {}
        errors = []

        for q_type, requested_count in question_type_config.items():
            available = db.query(Question).filter(
                Question.course_id == course_id,
                Question.question_type == q_type,
                Question.is_deleted == False
            ).count()

            available_counts[q_type] = available

            if available < requested_count:
                errors.append(
                    f"{q_type}: 请求{requested_count}题，但题库只有{available}题可用"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "available": available_counts
        }
