"""
S-CBR 螺旋推理系統 v2.0  # 🔧 版本號改為 v2.0

Spiral Case-Based Reasoning 系統
整合現有 Case 和 PulsePJ 知識庫的螺旋推理引擎

主要功能：
- 四步驟螺旋推理（搜尋、適配、監控、反饋）
- 螺旋互動推理（v2.0 新增）
- 會話狀態管理（v2.0 新增）
- Agentive AI 多智能體協作
- 脈診知識深度整合
- 完整的對話管理和狀態追蹤

版本：v2.0  # 🔧 版本號改為 v2.0
"""

from .main import run_spiral_cbr_v2, SpiralSessionManager
from .api import router

# 模組版本
__version__ = "2.0"  # 🔧 版本號改為 2.0

# 公開接口
__all__ = [
    "run_spiral_cbr_v2",  # 🔧 改為 v2
    "SpiralSessionManager",  # 🔧 新增
    "router",
    "__version__"
]

# 模組級別配置
SCBR_CONFIG = {
    "version": __version__,
    "description": "Spiral Case-Based Reasoning System v2.0",
    "features": [
        "four_step_spiral_reasoning",
        "spiral_interactive_reasoning",  # 🔧 新增
        "session_state_management",  # 🔧 新增
        "agentive_ai_collaboration",
        "pulse_knowledge_integration",
        "dialog_management",
        "state_tracking"
    ],
    "knowledge_bases": [
        "Case",
        "PulsePJ"
    ]
}

def get_version():
    """獲取 S-CBR 版本資訊"""
    return {
        "version": __version__,
        "config": SCBR_CONFIG
    }

# 初始化日誌
import logging
logging.getLogger("s_cbr").info(f"S-CBR v{__version__} 模組載入完成")
