"""
對話回合模型 v1.0

v1.0 功能：
- 對話回合資料結構
- 用戶輸入與系統回應追蹤
- 螺旋推理上下文記錄
- 時間戳與版本控制

版本：v1.0
"""

from typing import Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class DialogTurn:
    """
    對話回合模型 v1.0
    
    v1.0 特色：
    - 結構化對話回合記錄
    - 螺旋推理輪次追蹤
    - 步驟編號關聯
    - 完整元數據支持
    """
    
    turn_id: int
    session_id: str
    turn_type: str  # 'user_input' 或 'system_response'
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    spiral_round: int = 0
    step_number: int = 0
    version: str = "1.0"
    
    # 可選的額外屬性
    confidence_score: float = 0.0
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "turn_type": self.turn_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "spiral_round": self.spiral_round,
            "step_number": self.step_number,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
            "version": self.version
        }
    
    def get_content_summary(self) -> str:
        """獲取內容摘要"""
        if isinstance(self.content, dict):
            if self.turn_type == "user_input":
                return self.content.get("user_message", "用戶輸入")[:100]
            else:
                return self.content.get("system_response", "系統回應")[:100]
        else:
            return str(self.content)[:100]
    
    def is_spiral_step(self) -> bool:
        """判斷是否為螺旋推理步驟"""
        return self.step_number > 0 and self.spiral_round > 0
    
    def update_metadata(self, key: str, value: Any):
        """更新元數據"""
        self.metadata[key] = value
    
    def add_processing_info(self, processing_time: int, confidence: float = 0.0):
        """添加處理資訊"""
        self.processing_time_ms = processing_time
        self.confidence_score = confidence
    
    @classmethod
    def create_user_turn(cls, turn_id: int, session_id: str, user_input: Dict[str, Any], 
                        spiral_round: int = 0, step_number: int = 0) -> 'DialogTurn':
        """創建用戶輸入回合"""
        return cls(
            turn_id=turn_id,
            session_id=session_id,
            turn_type="user_input",
            content=user_input,
            spiral_round=spiral_round,
            step_number=step_number
        )
    
    @classmethod
    def create_system_turn(cls, turn_id: int, session_id: str, system_response: Dict[str, Any],
                          spiral_round: int = 0, step_number: int = 0, confidence: float = 0.0) -> 'DialogTurn':
        """創建系統回應回合"""
        return cls(
            turn_id=turn_id,
            session_id=session_id,
            turn_type="system_response",
            content=system_response,
            spiral_round=spiral_round,
            step_number=step_number,
            confidence_score=confidence
        )
