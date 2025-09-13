"""
S-CBR 對話模組 v1.0

提供對話管理功能：
- 對話狀態管理
- 回應生成
- 會話控制

版本：v1.0
"""

from .dialog_manager import DialogManager
from .conversation_state import ConversationState
from .response_generator import ResponseGenerator

__all__ = [
    "DialogManager",
    "ConversationState",
    "ResponseGenerator"
]
__version__ = "1.0"
