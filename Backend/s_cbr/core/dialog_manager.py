# -*- coding: utf-8 -*-
"""
累積式多輪對話管理
管理會話狀態與問題累積
"""
from typing import Dict, Any, Optional
from ..models.session import Session
from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("DialogManager")


class DialogManager:
    def __init__(self, config: SCBRConfig):
        self.config = config
        # { session_id: Session }
        self.sessions: Dict[str, Session] = {}

    def create_session(
        self,
        initial_question: str = "",
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        建立會話：
        - 若提供 session_id，將以該 ID 建立（覆蓋 Session 內的自動產生值）
        - 若未提供，使用 Session 內建機制產生
        回傳最終使用的 session_id
        """
        if patient_ctx is None:
            patient_ctx = {}

        session = Session(initial_question, patient_ctx)

        # ★ 若外部指定 session_id，覆蓋 Session 內的 id，確保呼叫端一致
        if isinstance(session_id, str) and session_id.strip():
            session.session_id = session_id.strip()

        # 寫入快取（若已存在則覆蓋，以最新為準）
        if session.session_id in self.sessions:
            logger.info(f"沿用既有會話: {session.session_id}")
        else:
            self.sessions[session.session_id] = session
            logger.info(f"會話建立: {session.session_id}")
        return session.session_id

    def continue_session(self, session_id: str, initial_question: str = "", patient_ctx: Optional[Dict[str, Any]] = None):
        """
        若不存在該 session，則自動建立一個（以避免 KeyError）
        """
        if session_id not in self.sessions:
            self.create_session(initial_question=initial_question, patient_ctx=patient_ctx or {}, session_id=session_id)
        logger.info(f"繼續會話: {session_id}")

    def increment_round(self, session_id: str) -> int:
        """
        將不存在的 session 視為新會話（round 從 0 → 1）
        """
        sess = self.sessions.setdefault(session_id, Session("", {}))
        # 防禦：確保為 int
        try:
            current = int(getattr(sess, "round_count", 0))
        except Exception:
            current = 0
        current += 1
        sess.round_count = current
        return current

    def record_step(self, session_id: str, step_result: Dict[str, Any]):
        """
        記錄單輪結果，若 session 不存在則自動建立空白再記錄
        """
        sess = self.sessions.setdefault(session_id, Session("", {}))
        # 初始化必要欄位
        if not hasattr(sess, "history"):
            sess.history = []
        if not hasattr(sess, "accumulated_question"):
            sess.accumulated_question = ""

        sess.history.append(step_result)
        reasoning = step_result.get("reasoning", "")
        if isinstance(reasoning, str) and reasoning:
            sess.accumulated_question = (sess.accumulated_question + " " + reasoning).strip()
        logger.info(f"記錄輪次 {getattr(sess, 'round_count', 0)} 結果於 {session_id}")

    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"刪除會話: {session_id}")
