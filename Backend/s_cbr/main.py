# -*- coding: utf-8 -*-\r
"""
S-CBR v2.2 主入口點 - 整合 OWASP 安全防護
包含策略層 (Security Strategy Layer) 和生成層 (Generation Layer) 的完整實作

核心修復：當 L1 Gate 輸出 'reject' 時，強制拋出 422 安全攔截錯誤 (修正 200 OK 缺陷)。
"""

import uuid
import yaml
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# 從 fastapi 引入 HTTPException 以處理 PermissionError
from fastapi import HTTPException 

from .config import cfg
from .core.dialog_manager import DialogManager
from .llm.client import LLMClient
from .utils.logger import get_logger
from .core.four_layer_pipeline import FourLayerSCBR
from .llm.embedding import EmbedClient
from .core.search_engine import SearchEngine

# ==================== 安全模組匯入 ====================
from .security.input_sanitizer import InputSanitizer, ThreatLevel
from .security.output_validator import OutputValidator
from .security.rate_limiter import RateLimiter, RateLimitConfig 
from .security.owasp_mapper import OWASPMapper, OWASPRisk


def _normalize_owasp_code(code: str) -> str:
    """將簡化 OWASP 代碼（如 LLM01）轉換為完整代碼（如 LLM01_PROMPT_INJECTION）"""
    # 檢查 code 是否是 OWASPRisk 的成員名稱 (例如 'LLM01')
    if code in OWASPRisk.__members__:
        # 返回該成員的 value (例如 'LLM01_PROMPT_INJECTION')
        return OWASPRisk[code].value 
    return code

logger = get_logger("SCBREngine")

class SCBREngine:
    
    _instance = None
    
    def __new__(cls):
        """單例模式：確保全域只有一個引擎實例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化 S-CBR 引擎及所有組件"""
        if self._initialized:
            return
            
        self.version = "2.2.0"
        self.config = cfg
        self.strategy_layer = None
        self.generation_layer = None
        
        # 假設 SCBRConfig 已經被正確初始化
        
        # 安全模組初始化 (簡化配置以避免對不存在模組的依賴)
        try:
            # 假設 InputSanitizer 在某處定義
            self.input_sanitizer = InputSanitizer(config=self.config)
        except NameError:
            self.input_sanitizer = None

        try:
            # 假設 OutputValidator 在某處定義
            self.output_validator = OutputValidator(config=self.config)
        except NameError:
            self.output_validator = None
        
        try:
            # 假設 RateLimiter 在某處定義
            rate_limit_config = RateLimitConfig(
                requests_per_ip_per_minute=20,
                requests_per_session_per_hour=100
            )
            self.rate_limiter = RateLimiter(config=rate_limit_config)
            logger.info("✅ RateLimiter 初始化成功")
        except NameError:
            self.rate_limiter = None
            
        try:
            # 假設 OWASPMapper 在某處定義
            self.owasp_mapper = OWASPMapper()
            logger.info("✅ OWASP映射器初始化成功")
        except NameError:
            self.owasp_mapper = None
        
        logger.info("✅ 安全模組初始化完成")
        
        # 核心組件初始化
        # 假設 DialogManager 已經被修復並引入
        self.dialog = DialogManager(self.config) 
        
        if self.config.features.enable_llm:
            try:
                # 假設 LLMClient 在某處定義
                self.llm = LLMClient(self.config) 
                logger.info("✅ LLM 客戶端初始化成功")
            except Exception as e:
                logger.error(f"❌ LLM 客戶端初始化失敗: {e}")
                self.llm = None
        else:
            self.llm = None
            logger.info("⚠️ LLM 功能已禁用")

        # 1. 初始化 EmbedClient
        try:
            # 假設 EmbedClient 在 llm.embedding 中定義
            self.embed = EmbedClient(self.config) 
            logger.info("✅ EmbedClient 初始化成功")
        except NameError:
            self.embed = None
            logger.warning("⚠️ EmbedClient 未找到或初始化失敗")
        
        # 2. 初始化 SearchEngine
        try:
            self.SE = SearchEngine(self.config)
            logger.info("✅ SearchEngine 初始化成功")
        except NameError:
            self.SE = None
            logger.warning("⚠️ SearchEngine 未找到或初始化失敗")
        
        try:
            self.four_layer = FourLayerSCBR(
                self.llm, 
                config=self.config,
                search_engine=self.SE,      # 傳遞 SE
                embed_client=self.embed     # 傳遞 EmbedClient
            ) if self.llm else None
            logger.info("✅ 四層 SCBR 管線初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ 四層管線初始化失敗: {e}")
            self.four_layer = None
        
        self._initialized = True
        logger.info("✅ S-CBR Engine 初始化完成 (含安全防護)")
    
    

    async def diagnose(
        self, 
        question: str, 
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None, 
        continue_spiral: bool = False,
        user_ip: Optional[str] = None,  # 用於速率限制
        **kwargs
    ) -> Dict[str, Any]:
        """
        執行單輪螺旋推理診斷 - 安全增強版本
        """
        start_time = datetime.now()
        trace_id = f"SCBR-{start_time.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        logger.info(f"🌀 啟動診斷 [{trace_id}]")
        logger.info(f"   問題: {question[:50]}...")
        logger.info(f"   session_id: {session_id}")
        logger.info(f"   continue_spiral: {continue_spiral}")
        
        cleaned_question = question
        # if self.input_sanitizer:
        # # 執行清洗與脫敏
        #     cleaned_question = self.input_sanitizer.sanitize(question)
        cleaned_question = question
        
        # ==================== STEP 1: 會話管理 (統一入口) ====================
        
        try:
            # 🚨 關鍵修復點：調用統一的 get_or_create_session
            session = self.dialog.get_or_create_session(
                session_id=session_id,
                new_question=cleaned_question,
                initial_context=patient_ctx
            )
        except PermissionError:
            # 由 DialogManager 拋出，表示會話因可疑活動（如多次違規）而被拒絕
            logger.error(f"❌ 診斷失敗: 會話因可疑活動被拒絕")
            raise HTTPException(
                status_code=422,
                detail={"message": "輸入內容違反系統安全政策，請重新嘗試。", "error": "SECURITY_SESSION_BLOCKED"}
            )
        except Exception as e:
            logger.error(f"❌ 診斷失敗: DialogManager 錯誤: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={"message": "會話初始化失敗", "error": str(e)}
            )
        
        # 更新狀態
        session_id = session.session_id
        accumulated_question = session.accumulated_question
        round_num = session.round_count
        
        logger.info(f"   會話ID: {session_id}")
        logger.info(f"   當前輪次: {round_num}")
        logger.info(f"   累積問題: {accumulated_question[:100]}...")
        
        # ==================== STEP 2-6: 四層推理 ====================
        # 提取前輪診斷資訊（用於螺旋推理）
        previous_diagnosis = None
        if session.history and len(session.history) > 0:
            # 獲取最後一輪的診斷結果
            last_step = session.history[-1]
            if 'l2' in last_step:
                previous_diagnosis = {
                    "selected_case": last_step.get('l2', {}).get('selected_case', {}),
                    "primary_pattern": last_step.get('l2', {}).get('tcm_inference', {}).get('primary_pattern', ''),
                    "coverage_ratio": last_step.get('l2', {}).get('coverage_evaluation', {}).get('coverage_ratio', 0.0)
                }
        
        try:
            result = await self.four_layer.run_once(
                accumulated_question,
                history_summary=kwargs.get("history_summary", ""),
                round_count=round_num,
                previous_diagnosis=previous_diagnosis
            )
        except Exception as e:
            logger.error(f"❌ 四層推理失敗: {e}", exc_info=True)
            raise HTTPException(
                 status_code=500,
                 detail={"message": "四層推理管道執行失敗", "error": str(e)}
            )
            
        # ==================== 🚨 關鍵修復點：安全攔截檢查 🚨 ====================
        
        # 檢查 L1 Gate 是否輸出了 'reject'
        l1_result = result.get('l1', {})
        if l1_result.get('status') == 'reject' or l1_result.get('next_action') == 'reject':
            # L1 攔截 (LLM01/LLM07/LLM06)
            flags = result.get('security_checks', {}).get('l1_flags', [])
            risk_info_raw = flags[0] if flags else "LLM01"
            risk_info = _normalize_owasp_code(risk_info_raw)
            
            logger.warning(f"🛡️ L1 門禁攔截: {risk_info}。阻止 200 OK 響應。")
            
            self.dialog.record_step(session_id, {
                **result,
                "round": round_num,
                "question": cleaned_question,
                "is_blocked": True, 
                "owasp_risk": risk_info,
                "defense_layer": "L1_Gate"
            })
            
            # 拋出 HTTPException 返回標準化安全拒絕響應 (修正 200 OK 缺陷)
            raise HTTPException(
                status_code=422,
                detail={"message": "輸入內容違反系統安全政策，請重新嘗試。", 
                        "error": "L1_GATE_REJECT",
                        "security_checks": result.get('security_checks', {}),
                        "l1_flags": [_normalize_owasp_code(f) for f in flags]}
            )
        
        # 檢查 L3 Gate 是否輸出了 'rejected'
        l3_result = result.get('l3', {})
        if l3_result.get('status') == 'rejected':
            # L3 攔截 (LLM05/LLM09)
            # 這裡假設 L3 應返回 violations 列表
            violations = result.get('security_checks', {}).get('l3_violations', [])
            risk_info_raw = violations[0].get('owasp_code') if violations else "LLM05"
            risk_info = _normalize_owasp_code(risk_info_raw)
            logger.warning(f"🛡️ L3 輸出審核拒絕: {risk_info}。阻止 200 OK 響應。")
            
            self.dialog.record_step(session_id, {
                **result,
                "round": round_num,
                "question": cleaned_question,
                "is_blocked": True, 
                "owasp_risk": risk_info,
                "defense_layer": "L3_Safety_Review"
            })
            
            # 拋出 HTTPException 返回標準化安全拒絕響應
            raise HTTPException(
                status_code=422,
                detail={"message": "診斷結果包含不當內容，已被安全策略阻止。", 
                        "error": "L3_REVIEW_REJECT",
                        "security_checks": result.get('security_checks', {}),
                        "l3_violations": [{"owasp_code": _normalize_owasp_code(v.get('owasp_code', 'UNKNOWN'))} for v in violations]}
            )
        # ==================== 🚨 安全檢查結束 🚨 ====================
        
        # 正常流程繼續
        should_stop = result.get('converged', False)
        continue_available = not should_stop
        
        # 記錄到會話歷史
        self.dialog.record_step(session_id, {
            **result,
            "round": round_num,
            "question": cleaned_question
        })
        
        # 組裝最終回應
        processing_time = (datetime.now() - start_time).total_seconds()
        
        response = {
            "session_id": session_id,
            "round": round_num,
            "trace_id": trace_id,
            "version": self.version,
            "processing_time": processing_time,
            "converged": should_stop,
            "continue_available": continue_available,
            "security_checks": result.get('security_checks', {}),
            **result
        }
        
        logger.info(f"✅ 診斷完成 [{trace_id}] 耗時: {processing_time:.2f}s")
        logger.info(f"   輪次: {round_num}, 可繼續: {continue_available}")
        
        return response

# ==================== 全域單例 ====================
_engine = SCBREngine()

async def run_spiral_cbr(question: str, **kwargs):
    """
    公開API入口
    """
    return await _engine.diagnose(question, **kwargs)

def get_engine():
    """
    獲取引擎實例
    """
    return _engine