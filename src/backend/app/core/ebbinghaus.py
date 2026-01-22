"""
艾宾浩斯复习算法工具类
"""
from datetime import datetime, timedelta


class EbbinghausScheduler:
    """艾宾浩斯记忆复习调度器"""

    # 复习间隔（分钟）
    REVIEW_INTERVALS = {
        0: 0,        # NEW - 新题
        1: 30,       # 30分钟后
        2: 720,      # 12小时
        3: 1440,     # 1天
        4: 2880,     # 2天
        5: 5760,     # 4天
        6: 10080,    # 7天
        7: 21600,    # 15天
    }

    MAX_STAGE = 8  # 已掌握

    @classmethod
    def calculate_next_review(cls, current_stage: int, is_correct: bool):
        """
        计算下次复习时间

        Args:
            current_stage: 当前复习阶段 (0-7)
            is_correct: 是否答对

        Returns:
            tuple: (next_stage, next_review_time or None)
        """
        if is_correct:
            next_stage = min(current_stage + 1, cls.MAX_STAGE)  # 8 = MASTERED
        else:
            next_stage = 1  # 回到第一阶段

        if next_stage == cls.MAX_STAGE:
            return next_stage, None  # 已掌握

        interval = cls.REVIEW_INTERVALS[next_stage]
        next_time = datetime.utcnow() + timedelta(minutes=interval)
        return next_stage, next_time

    @classmethod
    def get_due_review_ids(cls, user_id: str, current_time: datetime | None = None):
        """
        获取当前需要复习的题目ID列表

        Args:
            user_id: 用户ID
            current_time: 当前时间（默认为当前时间）

        Returns:
            list: 需要复习的题目ID列表
        """
        # 这个方法需要在数据库层面实现
        # 这里只是接口定义
        pass

    @classmethod
    def get_review_priority(cls, review_stage: int) -> int:
        """
        获取复习优先级

        优先级规则：
        1. 需要复习的错题（review_stage = 0 且 is_correct = False）
        2. 用户没刷过的题（review_stage = 0 且 is_correct = None）
        3. 已刷过但需要复习的题（review_stage > 0 且 next_review_time <= now）

        Args:
            review_stage: 复习阶段

        Returns:
            int: 优先级分数（越高越优先）
        """
        # 错题优先级最高
        # 新题次之
        # 复习题按 review_stage 排序，越早的越优先
        return review_stage
