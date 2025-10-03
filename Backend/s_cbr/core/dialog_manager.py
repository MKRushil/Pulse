# -*- coding: utf-8 -*-
"""
累積式多輪對話管理器
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("DialogManager")

class Session:
    """會話實體"""
    
    def __init__(self, initial_question: str = "", patient_ctx: Optional[Dict[str, Any]] = None):
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.round_count = 0
        self.accumulated_question = initial_question
        self.initial_question = initial_question
        self.patient_ctx = patient_ctx or {}
        self.history: List[Dict[str, Any]] = []
        self.last_case_id = None
        self.convergence_history = []
    
    def get_accumulated_question(self) -> str:
        """獲取累積問題"""
        return self.accumulated_question
    
    def add_question(self, new_question: str):
        """添加新問題到累積問題"""
        if new_question and new_question.strip():
            if self.accumulated_question:
                self.accumulated_question = f"{self.accumulated_question} {new_question}".strip()
            else:
                self.accumulated_question = new_question.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "round_count": self.round_count,
            "accumulated_question": self.accumulated_question,
            "initial_question": self.initial_question,
            "patient_ctx": self.patient_ctx,
            "history_count": len(self.history),
            "last_case_id": self.last_case_id
        }

class DialogManager:
    """對話管理器"""
    
    def __init__(self, config: SCBRConfig):
        self.config = config
        self.sessions: Dict[str, Session] = {}
        self.max_sessions = 100  # 最大會話數限制
        
        logger.info("對話管理器初始化完成")
    
    def create_session(
        self,
        initial_question: str = "",
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """創建新會話"""
        
        # 清理過期會話
        self._cleanup_old_sessions()
        
        session = Session(initial_question, patient_ctx)
        
        # 使用指定的 session_id 或生成的 ID
        if session_id:
            session.session_id = session_id
        
        self.sessions[session.session_id] = session
        
        logger.info(f"📝 創建會話: {session.session_id}")
        logger.info(f"   初始問題: {initial_question[:50]}...")
        
        return session.session_id
    
    def continue_session(
        self,
        session_id: str,
        new_question: str = "",
        patient_ctx: Optional[Dict[str, Any]] = None
    ):
        """繼續現有會話"""
        
        if session_id not in self.sessions:
            # 會話不存在，創建新的
            self.create_session(new_question, patient_ctx, session_id)
            logger.info(f"會話 {session_id} 不存在，已創建新會話")
        else:
            session = self.sessions[session_id]
            
            # 添加新問題到累積問題
            if new_question:
                session.add_question(new_question)
                logger.info(f"➕ 添加問題到會話 {session_id}: {new_question[:50]}...")
            
            # 更新患者上下文
            if patient_ctx:
                session.patient_ctx.update(patient_ctx)
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """獲取會話"""
        return self.sessions.get(session_id)
    
    def increment_round(self, session_id: str) -> int:
        """增加輪次計數"""
        session = self.sessions.get(session_id)
        if not session:
            session = Session()
            self.sessions[session_id] = session
        
        session.round_count += 1
        return session.round_count
    
    def record_step(self, session_id: str, step_result: Dict[str, Any]):
        """記錄推理步驟結果"""
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"會話 {session_id} 不存在，無法記錄步驟")
            return
        
        # 添加時間戳
        step_result["timestamp"] = datetime.now().isoformat()
        step_result["round"] = session.round_count
        
        # 記錄到歷史
        session.history.append(step_result)
        
        # 更新最後使用的案例ID
        if "primary" in step_result and step_result["primary"]:
            session.last_case_id = step_result["primary"].get("id")
        
        # 記錄收斂度
        if "convergence" in step_result:
            session.convergence_history.append(step_result["convergence"])
        
        logger.info(f"📊 記錄第 {session.round_count} 輪結果到會話 {session_id}")
    
    def reset_session(self, session_id: str):
        """重置會話"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"🔄 重置會話: {session_id}")
        else:
            logger.warning(f"嘗試重置不存在的會話: {session_id}")
    
    def _cleanup_old_sessions(self):
        """清理過期會話（保留最近的N個）"""
        if len(self.sessions) > self.max_sessions:
            # 按創建時間排序，刪除最舊的
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1].created_at
            )
            
            to_remove = len(self.sessions) - self.max_sessions
            for session_id, _ in sorted_sessions[:to_remove]:
                del self.sessions[session_id]
                logger.info(f"🗑️ 清理過期會話: {session_id}")
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """獲取會話摘要"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        return {
            **session.to_dict(),
            "convergence_trend": self._analyze_convergence_trend(session),
            "key_symptoms": self._extract_key_symptoms(session),
            "diagnosis_evolution": self._track_diagnosis_evolution(session)
        }
    
    def _analyze_convergence_trend(self, session: Session) -> Dict[str, Any]:
        """分析收斂趨勢"""
        if not session.convergence_history:
            return {"trend": "unknown", "values": []}
        
        values = [c.get("overall_convergence", 0) for c in session.convergence_history]
        
        # 計算趨勢
        if len(values) >= 2:
            recent_avg = sum(values[-3:]) / min(3, len(values))
            early_avg = sum(values[:3]) / min(3, len(values))
            trend = "improving" if recent_avg > early_avg else "stable"
        else:
            trend = "initializing"
        
        return {
            "trend": trend,
            "values": values,
            "current": values[-1] if values else 0
        }
    
    def _extract_key_symptoms(self, session: Session) -> List[str]:
        """提取關鍵症狀"""
        symptoms = set()
        for step in session.history:
            if "primary" in step and step["primary"]:
                hits = step["primary"].get("_hits", [])
                symptoms.update(hits)
        return list(symptoms)
    
    def _track_diagnosis_evolution(self, session: Session) -> List[Dict[str, Any]]:
        """追蹤診斷演化"""
        evolution = []
        for step in session.history:
            if "primary" in step and step["primary"]:
                evolution.append({
                    "round": step.get("round", 0),
                    "case_id": step["primary"].get("id"),
                    "score": step["primary"].get("_final", 0),
                    "diagnosis": step.get("diagnosis", "")
                })
        return evolution