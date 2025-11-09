# -*- coding: utf-8 -*-
"""
累積式多輪對話管理器 - 安全增強版本 (V2.2 最終修訂版)

主要安全功能：
- LLM02: 會話數據脫敏
- LLM10: 會話數量限制
- 數據完整性：會話驗證與清理

核心修復: 確保繼續會話時，不會錯誤地創建新會話，從而累積問題。
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hashlib

# 假設 SCBRConfig 和 logger 導入路徑正確
from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("DialogManager")

class Session:
    """
    會話實體 - 增強版本
    
    包含：
    - 基本會話資訊
    - 累積問題管理
    - 歷史記錄
    - 收斂度追蹤
    - ✅ 安全標記
    """
    
    def __init__(
        self,
        initial_question: str = "",
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        round_count: int = 1 # 確保初始輪次設定正確
    ):
        """
        初始化會話
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_accessed_at = datetime.now()
        self.round_count = round_count
        self.accumulated_question = initial_question
        self.initial_question = initial_question
        self.patient_ctx = patient_ctx or {}
        self.history: List[Dict[str, Any]] = []
        self.last_case_id = None
        self.convergence_history = []
        
        # 安全相關屬性
        self.security_flags = {
            "input_violations": 0,
            "suspicious_activity": False,
            "last_violation_time": None
        }
        
        # 資源限制
        self.max_history_length = 100
        self.max_accumulated_question_length = 5000
    
    def update_access_time(self):
        """
        更新最後訪問時間
        """
        self.last_accessed_at = datetime.now()
    
    def is_expired(self, max_idle_hours: int = 24) -> bool:
        """
        檢查會話是否過期
        """
        idle_time = datetime.now() - self.last_accessed_at
        return idle_time > timedelta(hours=max_idle_hours)
    
    def get_accumulated_question(self) -> str:
        """
        獲取累積問題
        """
        self.update_access_time()
        return self.accumulated_question
    
    def add_question(self, new_question: str):
        """
        添加新問題到累積問題（螺旋推理核心）
        
        會自動根據輪次調整累積問題的格式。
        
        Args:
            new_question: 新問題
        """
        if not new_question or not new_question.strip():
             return

        cleaned = new_question.strip()
        
        # 螺旋累積邏輯
        if self.round_count == 1:
            # Round 1 (由 create_session 處理，但安全起見重新賦值)
            self.accumulated_question = cleaned
        elif self.round_count == 2:
            # Round 2: 添加 "補充："
            self.accumulated_question = f"{self.accumulated_question}。補充：{cleaned}"
        else:
            # Round 3 及以後: 添加 "再補充："
            self.accumulated_question = f"{self.accumulated_question}。再補充：{cleaned}"

        # 長度限制檢查
        if len(self.accumulated_question) > self.max_accumulated_question_length:
            logger.warning(
                f"⚠️ 累積問題過長 ({len(self.accumulated_question)} 字符)，"
                f"已截斷最新內容。"
            )
            # 保留最新的內容
            self.accumulated_question = self.accumulated_question[-self.max_accumulated_question_length:]
        
        self.update_access_time()
        
    def record_security_violation(self, violation_type: str):
        """
        記錄安全違規
        """
        self.security_flags["input_violations"] += 1
        self.security_flags["last_violation_time"] = datetime.now()
        
        if self.security_flags["input_violations"] >= 3:
            self.security_flags["suspicious_activity"] = True
            logger.warning(
                f"🚨 會話 {self.session_id[:8]}*** 標記為可疑活動 "
                f"(違規次數: {self.security_flags['input_violations']})"
            )
    
    def is_suspicious(self) -> bool:
        """
        檢查是否為可疑會話
        """
        return self.security_flags["suspicious_activity"]
    
    def add_history_entry(self, entry: Dict[str, Any]):
        """
        添加歷史記錄項
        """
        self.history.append(entry)
        
        # 限制歷史記錄長度
        if len(self.history) > self.max_history_length:
            self.history = self.history[-self.max_history_length:]
            logger.warning(
                f"⚠️ 會話歷史過長，已清理至最新 {self.max_history_length} 條"
            )
    
    def get_session_hash(self) -> str:
        """
        獲取會話的雜湊值
        """
        content = f"{self.session_id}{self.created_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典（用於序列化）
        """
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
    
    # ----------------------------------------------------
    # 初始化與核心管理
    # ----------------------------------------------------

    def __init__(self, config: SCBRConfig):
        self.config = config
        self.sessions: Dict[str, Session] = {}
        
        # 資源限制配置
        self.max_sessions = 100
        self.max_idle_hours = 24
        self.cleanup_interval = 100
        self.session_create_count = 0
        
        logger.info(f"✅ 對話管理器初始化完成 (max_sessions={self.max_sessions})")
    
    def _create_new_session(
        self,
        initial_question: str = "",
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
        
        session = Session(initial_question, patient_ctx, session_id, round_count=1)
        final_session_id = session.session_id
        self.sessions[final_session_id] = session
        
        logger.info(f"🆕 創建會話: {final_session_id[:8]}***")
        logger.info(f"   初始問題: {initial_question[:50]}...")
        logger.info(f"   當前會話總數: {len(self.sessions)}")
        
        return final_session_id

    # ----------------------------------------------------
    # 核心會話查找與延續 (修復 L1 缺陷)
    # ----------------------------------------------------

    def get_or_create_session(
        self,
        session_id: Optional[str],
        new_question: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        功能描述: 查找現有會話並延續，或在找不到時創建新會話。
        
        修復重點: 確保當傳入 session_id 時，優先查找並延續，只有在 session 確實不存在時才創建新的。
        
        Args:
            session_id: 傳入的會話 ID。
            new_question: 客戶端傳入的當前問題。
            initial_context: 初始上下文 (如果創建新會話)。
            
        Returns:
            Session: 正在使用的 Session 實例。
        """
        # 1. 嘗試獲取現有會話
        session = self.sessions.get(session_id)
        
        if session:
            # 檢查是否過期或可疑
            if session.is_expired(self.max_idle_hours):
                logger.warning(f"⚠️ 會話 {session_id[:8]}*** 已過期，將創建新會話。")
                # 讓它走創建新會話的流程
            elif session.is_suspicious():
                logger.warning(f"🚨 會話 {session_id[:8]}*** 被標記為可疑，不予繼續。")
                raise PermissionError("會話因安全問題被拒絕。")
            else:
                # 2. 延續現有會話: 增加輪次並累積問題
                session.round_count += 1
                session.add_question(new_question) # 使用 add_question 處理螺旋累積前綴
                logger.info(f"🔄 延續會話: {session_id[:8]}***, 輪次: {session.round_count}")
                logger.info(f"   累積問題長度: {len(session.accumulated_question)}")
                return session

        # 3. 創建新會話: 如果 session_id 不存在、無效、或會話已過期
        final_session_id = self._create_new_session(
            initial_question=new_question, # 初始問題就是當前的問題
            patient_ctx=initial_context,
            session_id=None # 讓內部方法生成新的 ID
        )
        # 由於是新會話，它的 round_count 在 _create_new_session 中會是 1
        return self.sessions[final_session_id]

    # ----------------------------------------------------
    # 輔助工具
    # ----------------------------------------------------

    def _cleanup_expired_sessions(self):
        """清理過期會話"""
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
        """強制清理舊會話（當達到數量上限時）"""
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
        """
        記錄推理步驟結果 (現在依賴於 get_or_create_session 正確更新了 round_count)
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"⚠️ 會話 {session_id[:8]}*** 不存在，無法記錄步驟")
            return
        
        step_result["timestamp"] = datetime.now().isoformat()
        step_result["round"] = session.round_count # 使用會話內已更新的輪次
        
        session.add_history_entry(step_result)
        
        if "primary" in step_result and step_result["primary"]:
            session.last_case_id = step_result["primary"].get("id")
        
        if "convergence" in step_result:
            session.convergence_history.append(step_result["convergence"])
        
        logger.info(f"📊 記錄第 {session.round_count} 輪結果到會話 {session_id[:8]}***")

    def reset_session(self, session_id: str):
        """重置會話 (例如，當用戶明確開始新診斷時)"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"🔄 重置會話: {session_id[:8]}***")
        else:
            logger.warning(f"⚠️ 嘗試重置不存在的會話: {session_id[:8]}***")

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
        
        return list(symptoms)[:20]
    
    def _track_diagnosis_evolution(self, session: Session) -> List[Dict[str, Any]]:
        """追蹤診斷演化"""
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
        """
        獲取管理器統計資訊
        """
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