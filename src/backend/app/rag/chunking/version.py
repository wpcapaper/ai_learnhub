"""
分块策略版本控制

版本号格式：{策略类型}-v{major}.{minor}
- major: 不兼容变更（如完全重写分块逻辑）
- minor: 兼容性改进（如调整参数、修复边界情况）
"""

CHUNK_STRATEGY_VERSION = "markdown-v1.0"
CURRENT_STRATEGY_VERSION = CHUNK_STRATEGY_VERSION
