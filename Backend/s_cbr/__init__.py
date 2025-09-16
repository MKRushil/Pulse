"""
S-CBR 螺旋推理系統 v1.0

Spiral Case-Based Reasoning 系統
整合現有 Case 和 PulsePJ 知識庫的螺旋推理引擎

主要功能：
- 四步驟螺旋推理（搜尋、適配、監控、反饋）
- Agentive AI 多智能體協作
- 脈診知識深度整合
- 完整的對話管理和狀態追蹤

版本：v1.0
"""

from .main import run_spiral_cbr_v1
from .api import router

# 模組版本
__version__ = "1.0"

# 公開接口
__all__ = [
    "run_spiral_cbr_v1",  # 主要螺旋推理函數
    "router",             # FastAPI 路由器
    "__version__"
]

# 模組級別配置
SCBR_CONFIG = {
    "version": __version__,
    "description": "Spiral Case-Based Reasoning System",
    "features": [
        "four_step_spiral_reasoning",
        "agentive_ai_collaboration", 
        "pulse_knowledge_integration",
        "dialog_management",
        "state_tracking"
    ],
    "knowledge_bases": [
        "Case",      # 現有案例知識庫
        "PulsePJ"    # 現有脈診知識庫
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
