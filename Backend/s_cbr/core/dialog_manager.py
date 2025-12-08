# -*- coding: utf-8 -*-
"""
累積式多輪對話管理器 - 安全增強版本 (V2.3 兼容修訂版)

主要安全功能：
- LLM02: 會話數據脫敏
- LLM10: 會話數量限制
- 數據完整性：會話驗證與清理

修復紀錄: 
1. 確保繼續會話時，不會錯誤地創建新會話。
2. ✅ [FIX] 自動處理 SanitizationResult 物件，解決 object is not subscriptable 錯誤。
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import hashlib

# 假設 SCBRConfig 和 logger 導入路徑正確
from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("DialogManager")

class Session:
    """
    會話實體 - 增強版本
    """
    
    def __init__(
        self,
        initial_question: str = "",
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        round_count: int = 1 
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_accessed_at = datetime.now()
        self.round_count = round_count
        
        # 確保這裡是字串
        self.initial_question = self._ensure_string(initial_question)
        self.accumulated_question = self.initial_question
        
        self.patient_ctx = patient_ctx or {}
        self.history: List[Dict[str, Any]] = []
        self.last_case_id = None
        self.convergence_history = []
        # [NEW] 中醫思維：結構化狀態槽 (Structured State Slots)
        # 用於追蹤"已確認"與"已排除"的症狀，模擬醫生的心智模型
        self.confirmed_symptoms: List[str] = []  # 如: ["胃痛", "拒按"]
        self.ruled_out_symptoms: List[str] = []  # 如: ["口苦", "發熱"]
        self.suspected_pattern: str = ""
        
        # 安全相關屬性
        self.security_flags = {
            "input_violations": 0,
            "suspicious_activity": False,
            "last_violation_time": None
        }
        
        # 資源限制
        self.max_history_length = 100
        self.max_accumulated_question_length = 5000

    def _ensure_string(self, content: Any) -> str:
        """[FIX] 內部輔助：確保內容轉為字串"""
        if hasattr(content, 'cleaned_input'):
            return content.cleaned_input
        return str(content) if content is not None else ""
    
    def update_access_time(self):
        self.last_accessed_at = datetime.now()
    
    def is_expired(self, max_idle_hours: int = 24) -> bool:
        idle_time = datetime.now() - self.last_accessed_at
        return idle_time > timedelta(hours=max_idle_hours)
    
    def get_accumulated_question(self) -> str:
        self.update_access_time()
        return self.accumulated_question
    
    def add_question(self, new_question: Union[str, Any]):
        """
        添加新問題到累積問題（螺旋推理核心）
        ✅ [FIX] 支援 SanitizationResult 物件輸入
        """
        # 1. 處理 SanitizationResult 物件
        text_to_add = self._ensure_string(new_question)

        if not text_to_add or not text_to_add.strip():
             return

        cleaned = text_to_add.strip()
        
        # 螺旋累積邏輯
        if self.round_count == 1:
            self.accumulated_question = cleaned
        elif self.round_count == 2:
            self.accumulated_question = f"{self.accumulated_question}。補充：{cleaned}"
        else:
            self.accumulated_question = f"{self.accumulated_question}。再補充：{cleaned}"

        # 長度限制檢查
        if len(self.accumulated_question) > self.max_accumulated_question_length:
            logger.warning(
                f"⚠️ 累積問題過長 ({len(self.accumulated_question)} 字符)，"
                f"已截斷最新內容。"
            )
            self.accumulated_question = self.accumulated_question[-self.max_accumulated_question_length:]
        
        self.update_access_time()
        
    def record_security_violation(self, violation_type: str):
        self.security_flags["input_violations"] += 1
        self.security_flags["last_violation_time"] = datetime.now()
        
        if self.security_flags["input_violations"] >= 3:
            self.security_flags["suspicious_activity"] = True
            logger.warning(
                f"🚨 會話 {self.session_id[:8]}*** 標記為可疑活動 "
                f"(違規次數: {self.security_flags['input_violations']})"
            )
    
    def is_suspicious(self) -> bool:
        return self.security_flags["suspicious_activity"]
    
    def add_history_entry(self, entry: Dict[str, Any]):
        self.history.append(entry)
        if len(self.history) > self.max_history_length:
            self.history = self.history[-self.max_history_length:]
            logger.warning(f"⚠️ 會話歷史過長，已清理至最新 {self.max_history_length} 條")
    
    def get_session_hash(self) -> str:
        content = f"{self.session_id}{self.created_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_hash": self.get_session_hash(),
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "round_count": self.round_count,
            "accumulated_question_length": len(self.accumulated_question),
            "initial_question": self.initial_question[:100] + "...",
            "history_count": len(self.history),
            "last_case_id": self.last_case_id,
            "is_expired": self.is_expired(),
            "is_suspicious": self.is_suspicious(),
            "has_patient_context": bool(self.patient_ctx)
        }


class DialogManager:
    """
    對話管理器 - 安全增強版本
    """
    
    def __init__(self, config: SCBRConfig):
        self.config = config
        self.sessions: Dict[str, Session] = {}
        self.max_sessions = 100
        self.max_idle_hours = 24
        self.cleanup_interval = 100
        self.session_create_count = 0
        self.max_rounds = getattr(config, 'max_rounds', 7)
        logger.info(f"✅ 對話管理器初始化完成 (max_sessions={self.max_sessions})")
    
    def _extract_text(self, input_obj: Union[str, Any]) -> str:
        """✅ [FIX] 核心修復：從任意輸入中提取字串"""
        if isinstance(input_obj, str):
            return input_obj
        # 檢查是否為 SanitizationResult (Duck Typing)
        if hasattr(input_obj, 'cleaned_input'):
            return input_obj.cleaned_input
        return str(input_obj) if input_obj is not None else ""

    def _create_new_session(
        self,
        initial_question: Union[str, Any],
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """內部方法：實際創建新會話的邏輯"""
        self.session_create_count += 1
        if self.session_create_count % self.cleanup_interval == 0:
            self._cleanup_expired_sessions()
        
        if len(self.sessions) >= self.max_sessions:
            logger.warning(f"⚠️ 達到會話數量上限 ({self.max_sessions})，強制清理")
            self._force_cleanup_old_sessions()
        
        # ✅ [FIX] 確保傳入 Session 構造函數的是字串
        text_question = self._extract_text(initial_question)
        
        session = Session(text_question, patient_ctx, session_id, round_count=1)
        final_session_id = session.session_id
        self.sessions[final_session_id] = session
        
        logger.info(f"🆕 創建會話: {final_session_id[:8]}***")
        # 這裡不會再報錯，因為 text_question 已經轉為字串
        logger.info(f"   初始問題: {text_question[:50]}...") 
        logger.info(f"   當前會話總數: {len(self.sessions)}")
        
        return final_session_id

    def get_or_create_session(
        self,
        session_id: Optional[str],
        new_question: Union[str, Any], # 支援物件輸入
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        功能描述: 查找現有會話並延續，或在找不到時創建新會話。
        ✅ [FIX] 自動處理 SanitizationResult 物件
        """
        # 1. 嘗試獲取現有會話
        session = self.sessions.get(session_id)
        
        # 預先處理輸入文字
        text_question = self._extract_text(new_question)
        
        if session:
            # 檢查是否過期或可疑
            if session.is_expired(self.max_idle_hours):
                logger.warning(f"⚠️ 會話 {session_id[:8]}*** 已過期，將創建新會話。")
                
            elif session.is_suspicious():
                logger.warning(f"🚨 會話 {session_id[:8]}*** 被標記為可疑，不予繼續。")
                raise PermissionError("會話因安全問題被拒絕。")
            else:
                # 2. 延續現有會話
                session.round_count += 1
                session.add_question(text_question) # 使用純字串
                logger.info(f"🔄 延續會話: {session_id[:8]}***, 輪次: {session.round_count}")
                return session

        # 3. 創建新會話
        final_session_id = self._create_new_session(
            initial_question=text_question, # 使用純字串
            patient_ctx=initial_context,
            session_id=session_id
        )
        return self.sessions[final_session_id]

    # ----------------------------------------------------
    # 輔助工具
    # ----------------------------------------------------

    def _cleanup_expired_sessions(self):
        expired_ids = []
        for session_id, session in self.sessions.items():
            if session.is_expired(self.max_idle_hours):
                expired_ids.append(session_id)
        
        for session_id in expired_ids:
            del self.sessions[session_id]
            logger.info(f"🗑️ 清理過期會話: {session_id[:8]}***")
        
        if expired_ids:
            logger.info(f"✅ 清理了 {len(expired_ids)} 個過期會話")
    
    def _force_cleanup_old_sessions(self):
        if len(self.sessions) <= self.max_sessions:
            return
        
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_accessed_at
        )
        
        to_remove = len(self.sessions) - self.max_sessions
        
        for session_id, _ in sorted_sessions[:to_remove]:
            del self.sessions[session_id]
            logger.info(f"🗑️ 強制清理舊會話: {session_id[:8]}***")
        
        logger.info(f"✅ 強制清理了 {to_remove} 個舊會話")
    
    def record_step(self, session_id: str, step_result: Dict[str, Any]):
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"⚠️ 會話 {session_id[:8]}*** 不存在，無法記錄步驟")
            return
        
        step_result["timestamp"] = datetime.now().isoformat()
        step_result["round"] = session.round_count
        
        session.add_history_entry(step_result)
        
        if "primary" in step_result and step_result["primary"]:
            session.last_case_id = step_result["primary"].get("id")
        
        if "convergence" in step_result:
            session.convergence_history.append(step_result["convergence"])
        
        logger.info(f"📊 記錄第 {session.round_count} 輪結果到會話 {session_id[:8]}***")

    
    # [NEW] 實作螺旋對話更新與狀態追蹤
    def update_session(self, session_id: str, user_input: str, assistant_response: str) -> None:
        """
        更新會話歷史並執行簡單的狀態追蹤。
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"⚠️ 會話 {session_id[:8]}*** 不存在，無法更新")
            return
            
        # 1. 寫入對話歷史 (Memory)
        timestamp = datetime.now().isoformat()
        session.history.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        session.history.append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": timestamp
        })
        
        # 2. 結構化病歷累積 (Accumulation)
        # 避免重複添加，並加上輪次標記，模擬醫生寫病歷
        if user_input not in session.accumulated_question:
            time_tag = datetime.now().strftime("%H:%M")
            session.accumulated_question += f"；【Round {session.round_count} 補充】{user_input}"
            
        logger.info(f"📝 會話 {session_id[:8]}*** 歷史已更新 (Round {session.round_count})")
    
    
    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"🔄 重置會話: {session_id[:8]}***")
        else:
            logger.warning(f"⚠️ 嘗試重置不存在的會話: {session_id[:8]}***")

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
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
        if not session.convergence_history:
            return {"trend": "unknown", "values": []}
        
        values = [c.get("overall_convergence", 0) for c in session.convergence_history]
        
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
        symptoms = set()
        for step in session.history:
            if "primary" in step and step["primary"]:
                hits = step["primary"].get("_hits", [])
                symptoms.update(hits)
        
        return list(symptoms)[:20]
    
    def _track_diagnosis_evolution(self, session: Session) -> List[Dict[str, Any]]:
        evolution = []
        for step in session.history:
            if "primary" in step and step["primary"]:
                evolution.append({
                    "round": step.get("round", 0),
                    "case_id": step["primary"].get("id", "")[:16] + "***",
                    "score": step["primary"].get("_final", 0),
                    "diagnosis": step.get("diagnosis", "")
                })
        
        return evolution
    
    def get_statistics(self) -> Dict[str, Any]:
        active_sessions = [s for s in self.sessions.values() if not s.is_expired()]
        suspicious_sessions = [s for s in self.sessions.values() if s.is_suspicious()]
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active_sessions),
            "expired_sessions": len(self.sessions) - len(active_sessions),
            "suspicious_sessions": len(suspicious_sessions),
            "max_sessions_limit": self.max_sessions,
            "max_idle_hours": self.max_idle_hours
        }