# -*- coding: utf-8 -*-
"""
S-CBR v2.1 主入口點 - 修復輪次累加
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .config import cfg
from .core.spiral_engine import SpiralEngine
from .core.dialog_manager import DialogManager
from .core.convergence import ConvergenceMetrics
from .utils.logger import get_logger

logger = get_logger("SCBREngine")

class SCBREngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.config = cfg
        self.spiral = SpiralEngine(self.config)
        self.dialog = DialogManager(self.config)
        self.convergence = ConvergenceMetrics(self.config)
        self.version = "2.1.0"
        self._initialized = True
        
        logger.info("✅ S-CBR Engine 初始化完成")

    async def diagnose(
        self, 
        question: str, 
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None, 
        continue_spiral: bool = False
    ) -> Dict[str, Any]:
        """
        執行單輪螺旋推理診斷
        """
        start_time = datetime.now()
        trace_id = f"SCBR-{start_time.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        logger.info(f"🌀 啟動診斷 [{trace_id}]")
        logger.info(f"   問題: {question[:50]}...")
        logger.info(f"   session_id: {session_id}")
        logger.info(f"   continue_spiral: {continue_spiral}")
        
        # 檢測是否為補充條件（包含"補充條件："）
        is_supplement = "補充條件：" in question or "補充條件:" in question
        if is_supplement and session_id:
            continue_spiral = True
            logger.info("📝 檢測到補充條件，自動設置 continue_spiral=True")
        
        # 會話管理
        if not session_id:
            session_id = self.dialog.create_session(question, patient_ctx or {})
            logger.info(f"📝 創建新會話: {session_id}")
        elif continue_spiral:
            # 繼續會話時要增加輪次
            self.dialog.continue_session(session_id, question, patient_ctx)
            logger.info(f"➕ 繼續會話: {session_id}")
        else:
            # 新問題，重置會話
            session_id = self.dialog.create_session(question, patient_ctx or {})
            logger.info(f"🔄 重置會話: {session_id}")
        
        # 獲取累積問題
        session = self.dialog.get_session(session_id)
        accumulated_question = session.get_accumulated_question()
        
        # 記錄輪次（繼續推理時才增加）
        if continue_spiral:
            round_num = self.dialog.increment_round(session_id)
        else:
            round_num = 1
            session.round_count = 1
            
        logger.info(f"🔢 當前輪次: {round_num}")
        
        # 執行螺旋推理
        result = await self.spiral.execute_spiral_cycle(
            question=accumulated_question,
            session_id=session_id,
            round_num=round_num
        )
        
        # 計算收斂度
        convergence_metrics = self.convergence.calculate_convergence(
            session_id=session_id,
            current_result=result
        )
        
        # 記錄到會話歷史
        self.dialog.record_step(session_id, {
            **result,
            "convergence": convergence_metrics
        })
        
        # 判斷是否收斂
        should_stop = self.convergence.should_stop(convergence_metrics, round_num)
        
        # 決定是否可以繼續推理
        continue_available = not should_stop and round_num < self.config.spiral.max_rounds
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        response = {
            "session_id": session_id,
            "round": round_num,
            "converged": should_stop,
            "continue_available": continue_available,  # 添加這個字段
            "convergence_metrics": convergence_metrics,
            **result,
            "processing_time": processing_time,
            "trace_id": trace_id,
            "version": self.version
        }
        
        logger.info(f"✅ 診斷完成 [{trace_id}] 耗時: {processing_time:.2f}s")
        logger.info(f"   輪次: {round_num}, 可繼續: {continue_available}")
        
        return response

    def reset_session(self, session_id: str):
        """重置會話"""
        self.dialog.reset_session(session_id)
        self.convergence.clear_history(session_id)
        logger.info(f"🔄 會話重置: {session_id}")

# 全域單例
_engine = SCBREngine()

async def run_spiral_cbr(question: str, **kwargs):
    """公開API入口"""
    return await _engine.diagnose(question, **kwargs)

def get_engine():
    """獲取引擎實例"""
    return _engine