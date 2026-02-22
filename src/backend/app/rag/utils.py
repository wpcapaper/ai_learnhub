"""
RAG 工具函数

可独立导入的工具函数，不依赖外部库（如 chromadb）
"""
import re
import hashlib


def normalize_collection_name(name: str) -> str:
    """
    将任意字符串转换为合法的 ChromaDB collection 名称
    
    ChromaDB 要求: 3-512字符，只允许 [a-zA-Z0-9._-]，必须以字母或数字开头和结尾
    
    Args:
        name: 原始名称（可以是中文、特殊字符等）
    
    Returns:
        合法的 collection 名称
    """
    # 移除或替换非法字符
    normalized = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    
    # 确保以字母或数字开头
    if normalized and not normalized[0].isalnum():
        normalized = 'c_' + normalized
    
    # 确保以字母或数字结尾
    if normalized and not normalized[-1].isalnum():
        normalized = normalized + '_0'
    
    # 如果规范化后太短或为空，使用 hash
    if len(normalized) < 3:
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        normalized = f"col_{hash_suffix}"
    
    # 限制长度
    if len(normalized) > 512:
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        normalized = normalized[:503] + '_' + hash_suffix
    
    return normalized
