# -*- coding: utf-8 -*-
"""
S-CBR v2.1 主入口點 - 修復重複會話問題
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .config import SCBRConfig
from .core.spiral_engine import SpiralEngine
from .core.dialog_manager import DialogManager
from .utils.logger import get_logger

_config = SCBRConfig()
_spiral_engine = SpiralEngine(_config)
_dialog_manager = DialogManager(_config)
logger = get_logger("SCBREngine")

class SCBREngine:
    def __init__(self):
        self.config = _config
        self.spiral = _spiral_engine
        self.dialog = _dialog_manager
        self.version = "2.1.0"

    async def diagnose(self, question: str, patient_ctx: Optional[Dict[str,Any]] = None,
                       session_id: Optional[str] = None, continue_spiral: bool = False) -> Dict[str,Any]:
        start = datetime.now()
        trace_id = f"SCBR-{start.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        logger.info(f"🌀 啟動診斷 [{trace_id}] 問題: {question}")
        
        # 🔧 修正：統一會話管理邏輯
        if not session_id:
            # 沒有 session_id，創建新會話
            session_id = self.dialog.create_session(question, patient_ctx or {})
        elif continue_spiral:
            # 有 session_id 且要繼續推理，檢查會話是否存在
            if session_id not in self.dialog.sessions:
                # 會話不存在，重新創建
                session_id = self.dialog.create_session(question, patient_ctx or {})
            else:
                # 會話存在，直接繼續（不再調用 continue_session）
                logger.info(f"繼續既有會話: {session_id}")
        else:
            # 有 session_id 但不繼續推理，創建新會話
            session_id = self.dialog.create_session(question, patient_ctx or {})
        
        # 執行推理（只執行一次）
        result = await self.spiral.execute_spiral_cycle(question, session_id)
        processing = (datetime.now()-start).total_seconds()
        
        response = {
            "session_id": session_id,
            **result,
            "processing_time": processing,
            "trace_id": trace_id,
            "version": self.version
        }
        return response

async def run_spiral_cbr(question: str, **kwargs):
    engine = SCBREngine()
    return await engine.diagnose(question, **kwargs)
