"""
S-CBR Knowledge 模組 v1.0

v1.0 功能：
- 知識庫統一管理接口
- Case 和 Pulse 知識庫整合
- 反饋學習機制
- 螺旋推理記憶管理

版本：v1.0
"""

from .case_repository import CaseRepository
from .feedback_repository import FeedbackRepository  
from .spiral_memory import SpiralMemory

__version__ = "1.0"

__all__ = [
    "CaseRepository",
    "FeedbackRepository", 
    "SpiralMemory"
]

# v1.0 知識模組初始化
def initialize_knowledge_repositories():
    """初始化所有知識庫"""
    case_repo = CaseRepository()
    feedback_repo = FeedbackRepository()
    spiral_memory = SpiralMemory()
    
    return {
        'case_repository': case_repo,
        'feedback_repository': feedback_repo,
        'spiral_memory': spiral_memory
    }
