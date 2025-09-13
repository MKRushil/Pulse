"""
S-CBR 核心模組 v1.0

提供核心推理功能：
- 螺旋 CBR 推理引擎
- Agentive AI 協調器
- 對話編排器

版本：v1.0
"""

from .spiral_cbr_engine import SpiralCBREngine
from .agentive_coordinator import AgentiveCoordinator
from .dialog_orchestrator import DialogOrchestrator

__all__ = [
    "SpiralCBREngine", 
    "AgentiveCoordinator", 
    "DialogOrchestrator"
]
__version__ = "1.0"
