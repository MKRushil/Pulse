"""
Agentive 狀態模型 v1.0

v1.0 功能：
- 多智能體狀態同步
- 上下文共享管理
- 協作狀態追蹤
- 智能體間通訊記錄

版本：v1.0
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class AgentType(Enum):
    """智能體類型枚舉"""
    DIAGNOSTIC = "diagnostic_agent"
    ADAPTATION = "adaptation_agent"
    MONITORING = "monitoring_agent"
    FEEDBACK = "feedback_agent"
    COORDINATOR = "agentive_coordinator"

class AgentStatus(Enum):
    """智能體狀態枚舉"""
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class AgentiveState:
    """
    Agentive 狀態管理模型 v1.0
    
    v1.0 特色：
    - 多智能體協作狀態
    - 實時狀態同步
    - 智能體間資訊共享
    - 協作效能追蹤
    """
    
    # 基本標識
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    
    # 智能體狀態追蹤
    agent_states: Dict[AgentType, Dict[str, Any]] = field(default_factory=dict)
    agent_status: Dict[AgentType, AgentStatus] = field(default_factory=dict)
    
    # 共享上下文
    shared_context: Dict[str, Any] = field(default_factory=dict)
    global_insights: Dict[str, Any] = field(default_factory=dict)
    
    # v1.0 脈診專用共享狀態
    pulse_knowledge_context: Dict[str, Any] = field(default_factory=dict)
    pulse_integration_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 協作歷史
    collaboration_history: List[Dict[str, Any]] = field(default_factory=list)
    inter_agent_messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # 效能追蹤
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    decision_confidence: float = 0.0
    collaboration_quality: float = 0.0
    
    # 錯誤追蹤
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    def initialize_agent(self, agent_type: AgentType, initial_state: Dict[str, Any] = None):
        """初始化智能體狀態"""
        self.agent_states[agent_type] = initial_state or {}
        self.agent_status[agent_type] = AgentStatus.IDLE
        self.last_updated = datetime.now()
    
    def update_agent_state(self, agent_type: AgentType, state_data: Dict[str, Any]):
        """更新智能體狀態"""
        if agent_type not in self.agent_states:
            self.initialize_agent(agent_type)
        
        self.agent_states[agent_type].update(state_data)
        self.last_updated = datetime.now()
    
    def set_agent_status(self, agent_type: AgentType, status: AgentStatus):
        """設置智能體狀態"""
        self.agent_status[agent_type] = status
        self.last_updated = datetime.now()
    
    def update_shared_context(self, context_key: str, context_value: Any):
        """更新共享上下文"""
        self.shared_context[context_key] = context_value
        self.last_updated = datetime.now()
    
    def add_global_insight(self, insight_key: str, insight_data: Dict[str, Any]):
        """添加全局洞察"""
        self.global_insights[insight_key] = {
            **insight_data,
            "timestamp": datetime.now().isoformat(),
            "version": self.version
        }
        self.last_updated = datetime.now()
    
    def update_pulse_context_v1(self, pulse_data: Dict[str, Any]):
        """更新脈診上下文 v1.0"""
        self.pulse_knowledge_context.update(pulse_data)
        
        # 記錄脈診整合歷史
        self.pulse_integration_history.append({
            "data": pulse_data,
            "timestamp": datetime.now().isoformat(),
            "integration_quality": pulse_data.get("integration_quality", 0.0)
        })
        
        # 保持歷史記錄大小
        if len(self.pulse_integration_history) > 20:
            self.pulse_integration_history = self.pulse_integration_history[-15:]
        
        self.last_updated = datetime.now()
    
    def log_collaboration(self, source_agent: AgentType, target_agent: AgentType, 
                         interaction_type: str, data: Dict[str, Any]):
        """記錄智能體協作"""
        collaboration_entry = {
            "source": source_agent.value,
            "target": target_agent.value,
            "interaction_type": interaction_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id
        }
        
        self.collaboration_history.append(collaboration_entry)
        
        # 保持協作歷史大小
        if len(self.collaboration_history) > 50:
            self.collaboration_history = self.collaboration_history[-30:]
        
        self.last_updated = datetime.now()
    
    def send_inter_agent_message(self, from_agent: AgentType, to_agent: AgentType,
                                message_type: str, message_content: Dict[str, Any]):
        """發送智能體間消息"""
        message = {
            "message_id": len(self.inter_agent_messages) + 1,
            "from_agent": from_agent.value,
            "to_agent": to_agent.value,
            "message_type": message_type,
            "content": message_content,
            "timestamp": datetime.now().isoformat(),
            "processed": False
        }
        
        self.inter_agent_messages.append(message)
        self.last_updated = datetime.now()
    
    def get_pending_messages(self, agent_type: AgentType) -> List[Dict[str, Any]]:
        """獲取待處理消息"""
        return [
            msg for msg in self.inter_agent_messages
            if msg["to_agent"] == agent_type.value and not msg["processed"]
        ]
    
    def mark_message_processed(self, message_id: int):
        """標記消息已處理"""
        for msg in self.inter_agent_messages:
            if msg["message_id"] == message_id:
                msg["processed"] = True
                msg["processed_at"] = datetime.now().isoformat()
                break
        self.last_updated = datetime.now()
    
    def add_error(self, agent_type: AgentType, error_message: str, error_details: Dict[str, Any] = None):
        """添加錯誤記錄"""
        error_entry = {
            "agent": agent_type.value,
            "error_message": error_message,
            "error_details": error_details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.errors.append(error_entry)
        self.set_agent_status(agent_type, AgentStatus.ERROR)
    
    def add_warning(self, agent_type: AgentType, warning_message: str, warning_details: Dict[str, Any] = None):
        """添加警告記錄"""
        warning_entry = {
            "agent": agent_type.value,
            "warning_message": warning_message,
            "warning_details": warning_details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.warnings.append(warning_entry)
    
    def calculate_collaboration_quality_v1(self) -> float:
        """計算協作品質 v1.0"""
        if not self.collaboration_history:
            return 0.0
        
        # 基於協作頻率和成功率
        recent_collaborations = [
            c for c in self.collaboration_history
            if (datetime.now() - datetime.fromisoformat(c["timestamp"])).seconds < 3600  # 1小時內
        ]
        
        if not recent_collaborations:
            return 0.5  # 中性分數
        
        # 成功協作比例（簡化判斷：無錯誤的協作）
        successful_collaborations = len([
            c for c in recent_collaborations
            if not any(e["timestamp"] >= c["timestamp"] for e in self.errors)
        ])
        
        success_rate = successful_collaborations / len(recent_collaborations) if recent_collaborations else 0
        
        # v1.0 脈診協作品質
        pulse_collaborations = [
            c for c in recent_collaborations
            if "pulse" in c.get("interaction_type", "").lower()
        ]
        pulse_quality_bonus = min(0.2, len(pulse_collaborations) * 0.1)  # 最多0.2分加分
        
        collaboration_quality = success_rate + pulse_quality_bonus
        
        self.collaboration_quality = min(1.0, collaboration_quality)
        return self.collaboration_quality
    
    def update_performance_metrics(self, metrics: Dict[str, Any]):
        """更新效能指標"""
        self.performance_metrics.update(metrics)
        self.performance_metrics["last_updated"] = datetime.now().isoformat()
        self.last_updated = datetime.now()
    
    def get_state_summary(self) -> Dict[str, Any]:
        """獲取狀態摘要"""
        active_agents = [agent.value for agent, status in self.agent_status.items() 
                        if status != AgentStatus.IDLE]
        
        return {
            "session_id": self.session_id,
            "active_agents": active_agents,
            "total_agents": len(self.agent_states),
            "collaboration_events": len(self.collaboration_history),
            "pending_messages": len([msg for msg in self.inter_agent_messages if not msg["processed"]]),
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "pulse_integrations": len(self.pulse_integration_history),  # v1.0
            "collaboration_quality": self.calculate_collaboration_quality_v1(),
            "decision_confidence": self.decision_confidence,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "version": self.version
        }
    
    def get_agent_summary(self, agent_type: AgentType) -> Optional[Dict[str, Any]]:
        """獲取特定智能體摘要"""
        if agent_type not in self.agent_states:
            return None
        
        agent_collaborations = [
            c for c in self.collaboration_history
            if c["source"] == agent_type.value or c["target"] == agent_type.value
        ]
        
        agent_errors = [e for e in self.errors if e["agent"] == agent_type.value]
        agent_warnings = [w for w in self.warnings if w["agent"] == agent_type.value]
        
        return {
            "agent_type": agent_type.value,
            "current_status": self.agent_status.get(agent_type, AgentStatus.IDLE).value,
            "state_data": self.agent_states[agent_type],
            "collaboration_count": len(agent_collaborations),
            "error_count": len(agent_errors),
            "warning_count": len(agent_warnings),
            "last_collaboration": agent_collaborations[-1]["timestamp"] if agent_collaborations else None,
            "performance_summary": self._calculate_agent_performance(agent_type)
        }
    
    def _calculate_agent_performance(self, agent_type: AgentType) -> Dict[str, Any]:
        """計算智能體效能"""
        # 簡化效能計算
        agent_errors = len([e for e in self.errors if e["agent"] == agent_type.value])
        agent_collaborations = len([
            c for c in self.collaboration_history
            if c["source"] == agent_type.value or c["target"] == agent_type.value
        ])
        
        error_rate = agent_errors / max(agent_collaborations, 1)
        performance_score = max(0.0, 1.0 - error_rate)
        
        return {
            "performance_score": performance_score,
            "error_rate": error_rate,
            "collaboration_activity": agent_collaborations,
            "status_stability": "stable" if agent_errors == 0 else "needs_attention"
        }
    
    def cleanup_old_data(self, retention_hours: int = 24):
        """清理舊資料"""
        cutoff_time = datetime.now() - datetime.timedelta(hours=retention_hours)
        
        # 清理舊的協作記錄
        self.collaboration_history = [
            c for c in self.collaboration_history
            if datetime.fromisoformat(c["timestamp"]) > cutoff_time
        ]
        
        # 清理舊的消息
        self.inter_agent_messages = [
            msg for msg in self.inter_agent_messages
            if datetime.fromisoformat(msg["timestamp"]) > cutoff_time
        ]
        
        # 清理舊的脈診整合歷史
        self.pulse_integration_history = [
            p for p in self.pulse_integration_history
            if datetime.fromisoformat(p["timestamp"]) > cutoff_time
        ]
        
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "version": self.version,
            "agent_states": {k.value: v for k, v in self.agent_states.items()},
            "agent_status": {k.value: v.value for k, v in self.agent_status.items()},
            "shared_context": self.shared_context,
            "global_insights": self.global_insights,
            "pulse_knowledge_context": self.pulse_knowledge_context,
            "pulse_integration_history": self.pulse_integration_history,
            "collaboration_history": self.collaboration_history,
            "inter_agent_messages": self.inter_agent_messages,
            "performance_metrics": self.performance_metrics,
            "decision_confidence": self.decision_confidence,
            "collaboration_quality": self.collaboration_quality,
            "errors": self.errors,
            "warnings": self.warnings,
            "state_summary": self.get_state_summary()
        }
