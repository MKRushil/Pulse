"""
S-CBR (Spiral Case-Based Reasoning) 螺旋案例推理系統 v1.0

本模組實現基於螺旋推理的中醫診斷系統，整合現有 Weaviate 知識庫：
- Case class: 真實案例知識庫
- PulsePJ class: 28脈診相關知識庫

主要功能：
- 四步驟螺旋推理循環 (STEP 1-4)
- Agentive AI 多智能體協作
- 對話式交互管理
- 反饋學習機制

版本：1.0
作者：S-CBR Team
更新日期：2025-09-13
"""

__version__ = "1.0"
__author__ = "S-CBR Team"
__update_date__ = "2025-09-13"

# 主要導入
from .main import SCBREngine
from .core.spiral_cbr_engine import SpiralCBREngine
from .config.scbr_config import SCBRConfig

__all__ = [
    "SCBREngine",
    "SpiralCBREngine", 
    "SCBRConfig"
]

