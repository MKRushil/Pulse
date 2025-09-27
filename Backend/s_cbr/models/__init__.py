"""
S-CBR 資料模型 v1.0

提供資料結構定義：
- 螺旋案例模型
- 對話回合模型
- 反饋案例模型
- Agentive 狀態模型

版本：v1.0
"""

from .spiral_case import SpiralCase, SpiralState
from .dialog_turn import DialogTurn
from .feedback_case import FeedbackCase
from .agentive_state import AgentiveState

__all__ = [
    "SpiralCase",
    "SpiralState", 
    "DialogTurn",
    "FeedbackCase",
    "AgentiveState"
]
__version__ = "1.0"
