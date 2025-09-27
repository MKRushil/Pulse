"""
螺旋推理會話管理模組 v2.0

提供螺旋推理會話的完整管理功能：
- SpiralSession: 單個會話管理
- SpiralSessionManager: 全域會話管理

版本: v2.0
作者: S-CBR Team
更新時間: 2025-09-16
"""

from .spiral_session import SpiralSession
from .spiral_session_manager import SpiralSessionManager

# 模組版本
__version__ = "2.0"

# 公開接口
__all__ = [
    "SpiralSession",
    "SpiralSessionManager",
    "__version__"
]

# 模組配置
SESSIONS_CONFIG = {
    "version": __version__,
    "description": "Spiral Reasoning Session Management",
    "features": [
        "session_state_tracking",
        "case_usage_recording", 
        "query_similarity_detection",
        "automatic_session_cleanup",
        "thread_safe_operations",
        "session_statistics"
    ],
    "default_settings": {
        "max_sessions": 1000,
        "session_timeout_hours": 24,
        "similarity_threshold": 0.8,
        "max_cases_per_session": 10
    }
}

def create_session_manager(max_sessions: int = 1000) -> SpiralSessionManager:
    """
    創建會話管理器的便捷函數
    
    Args:
        max_sessions: 最大會話數，默認1000
        
    Returns:
        SpiralSessionManager: 會話管理器實例
    """
    return SpiralSessionManager(max_sessions=max_sessions)

def get_module_info():
    """
    獲取模組信息
    
    Returns:
        dict: 模組配置信息
    """
    return SESSIONS_CONFIG

# 模組初始化日誌
import logging
logger = logging.getLogger(__name__)
logger.info(f"S-CBR Sessions 模組 v{__version__} 載入完成")
logger.debug(f"支援功能: {', '.join(SESSIONS_CONFIG['features'])}")