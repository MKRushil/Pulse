"""
對話狀態管理 v1.0

v1.0 功能：
- 對話狀態追蹤
- 會話上下文管理
- 螺旋推理狀態記錄
- 多輪對話支持

版本：v1.0
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class ConversationState:
    """
    對話狀態管理類 v1.0
    
    v1.0 特色：
    - 螺旋推理狀態追蹤
    - 患者上下文記錄
    - 多輪對話支持
    - 狀態持久化
    """
    
    # 基本會話資訊
    session_id: str = ""
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # 對話狀態
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)
    
    # 患者上下文
    patient_context: Dict[str, Any] = field(default_factory=dict)
    
    # 螺旋推理狀態
    spiral_rounds: int = 0
    current_step: str = ""
    reasoning_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 版本資訊
    version: str = "1.0"
    
    def __init__(self, session_id: str = None, spiral_state=None, version: str = "1.0"):
        """初始化對話狀態"""
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.user_id = None
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.conversation_history = []
        self.current_state = {}
        self.patient_context = {}
        self.spiral_rounds = 0
        self.current_step = ""
        self.reasoning_history = []
        self.version = version
        
        # 如果提供了 spiral_state，整合其資訊
        if spiral_state:
            self.spiral_rounds = getattr(spiral_state, 'current_round', 0)
            self.current_step = getattr(spiral_state, 'current_step', '')
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """獲取狀態值"""
        return self.current_state.get(key, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """設置狀態值"""
        self.current_state[key] = value
        self.last_updated = datetime.now()
    
    def update_patient_context(self, context: Dict[str, Any]) -> None:
        """更新患者上下文"""
        self.patient_context.update(context)
        self.last_updated = datetime.now()
    
    def add_conversation_turn(self, turn_type: str, content: Dict[str, Any]) -> None:
        """添加對話輪次"""
        turn = {
            "turn_id": len(self.conversation_history) + 1,
            "turn_type": turn_type,  # 'user' 或 'system'
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "spiral_round": self.spiral_rounds
        }
        self.conversation_history.append(turn)
        self.last_updated = datetime.now()
    
    def add_system_response(self, response: Dict[str, Any]) -> None:
        """添加系統回應"""
        self.add_conversation_turn("system", response)
    
    def add_user_input(self, user_input: Dict[str, Any]) -> None:
        """添加用戶輸入"""
        self.add_conversation_turn("user", user_input)
    
    def start_new_spiral_round(self) -> None:
        """開始新的螺旋推理輪次"""
        self.spiral_rounds += 1
        self.current_step = "search"
        self.last_updated = datetime.now()
    
    def update_spiral_step(self, step: str, result: Dict[str, Any] = None) -> None:
        """更新螺旋推理步驟"""
        self.current_step = step
        
        if result:
            step_record = {
                "round": self.spiral_rounds,
                "step": step,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            self.reasoning_history.append(step_record)
        
        self.last_updated = datetime.now()
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """獲取對話摘要"""
        return {
            "session_id": self.session_id,
            "total_turns": len(self.conversation_history),
            "spiral_rounds": self.spiral_rounds,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "has_patient_context": bool(self.patient_context),
            "version": self.version
        }
    
    def reset_state(self) -> None:
        """重置對話狀態"""
        self.current_state.clear()
        self.conversation_history.clear()
        self.patient_context.clear()
        self.reasoning_history.clear()
        self.spiral_rounds = 0
        self.current_step = ""
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "conversation_history": self.conversation_history,
            "current_state": self.current_state,
            "patient_context": self.patient_context,
            "spiral_rounds": self.spiral_rounds,
            "current_step": self.current_step,
            "reasoning_history": self.reasoning_history,
            "version": self.version
        }

# 匯出類
__all__ = ["ConversationState"]
