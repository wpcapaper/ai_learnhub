"""评估指标计算"""

from typing import List, Set


def calculate_recall(
    retrieved: Set[str],
    relevant: Set[str]
) -> float:
    """
    计算召回率
    
    Args:
        retrieved: 检索到的ID集合
        relevant: 相关的ID集合
    
    Returns:
        召回率 (0-1)
    """
    if not relevant:
        return 0.0
    
    intersection = retrieved & relevant
    return len(intersection) / len(relevant)


def calculate_precision(
    retrieved: Set[str],
    relevant: Set[str]
) -> float:
    """
    计算精确率
    
    Args:
        retrieved: 检索到的ID集合
        relevant: 相关的ID集合
    
    Returns:
        精确率 (0-1)
    """
    if not retrieved:
        return 0.0
    
    intersection = retrieved & relevant
    return len(intersection) / len(retrieved)


def calculate_mrr(
    retrieved: List[str],
    relevant: Set[str]
) -> float:
    """
    计算平均倒数排名 (Mean Reciprocal Rank)
    
    Args:
        retrieved: 检索到的ID列表（按顺序）
        relevant: 相关的ID集合
    
    Returns:
        MRR值 (0-1)
    """
    if not relevant:
        return 0.0
    
    for rank, item_id in enumerate(retrieved, 1):
        if item_id in relevant:
            return 1.0 / rank
    
    return 0.0


def calculate_f1_score(
    retrieved: Set[str],
    relevant: Set[str]
) -> float:
    """
    计算F1分数
    
    Args:
        retrieved: 检索到的ID集合
        relevant: 相关的ID集合
    
    Returns:
        F1分数 (0-1)
    """
    precision = calculate_precision(retrieved, relevant)
    recall = calculate_recall(retrieved, relevant)
    
    if precision + recall == 0:
        return 0.0
    
    return 2 * (precision * recall) / (precision + recall)
