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
from .llm.client import LLMClient
from .utils.logger import get_logger
from .core.stop_criteria import StopCriteriaManager
from .core.gap_asker import GapAsker
from .core.pattern_shifter import PatternShifter
from .core.self_reviewer import SelfReviewer

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
            
        self.version = "2.1.0"
        self.config = cfg
        
        # ==================== 1. 基礎組件初始化 ====================
        self.dialog = DialogManager(self.config)
        self.convergence = ConvergenceMetrics(self.config)
        
        # ==================== 2. LLM 初始化（必須在 SelfReviewer 之前） ====================
        if self.config.features.enable_llm:
            try:
                self.llm = LLMClient(self.config)
                logger.info("✅ LLM 客戶端初始化成功")
            except Exception as e:
                logger.error(f"❌ LLM 客戶端初始化失敗: {e}")
                self.llm = None
        else:
            self.llm = None
            logger.info("⚠️  LLM 功能已禁用")
        
        # ==================== 3. SpiralEngine 初始化 ====================
        self.spiral = SpiralEngine(
            self.config,
            dialog_manager=self.dialog
        )
        
        # ==================== 4. 輔助模組初始化 ====================
        try:
            self.stop_criteria = StopCriteriaManager()
            self.gap_asker = GapAsker()
            self.pattern_shifter = PatternShifter()
            self.self_reviewer = SelfReviewer(llm_client=self.llm)  # ✅ 現在 self.llm 已定義
            logger.info("✅ 輔助模組初始化完成")
        except Exception as e:
            logger.warning(f"⚠️  輔助模組初始化失敗: {e}")
            import traceback
            traceback.print_exc()
            self.stop_criteria = None
            self.gap_asker = None
            self.pattern_shifter = None
            self.self_reviewer = None
        
        self._initialized = True
        logger.info("✅ S-CBR Engine 初始化完成")

    async def diagnose(
        self, 
        question: str, 
        patient_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None, 
        continue_spiral: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        執行單輪螺旋推理診斷
        
        Args:
            question: 用戶問題/症狀描述
            patient_ctx: 患者上下文信息
            session_id: 會話ID（None時創建新會話）
            continue_spiral: 是否繼續現有會話
            **kwargs: 額外參數（如 user_satisfied）
        
        Returns:
            診斷結果字典
        """
        start_time = datetime.now()
        trace_id = f"SCBR-{start_time.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        logger.info(f"🌀 啟動診斷 [{trace_id}]")
        logger.info(f"   問題: {question[:50]}...")
        logger.info(f"   session_id: {session_id}")
        logger.info(f"   continue_spiral: {continue_spiral}")
        
        # ==================== STEP 1: 會話管理 ====================
        # 檢測是否為補充條件（包含"補充條件："）
        is_supplement = "補充條件：" in question or "補充條件:" in question
        if is_supplement and session_id:
            continue_spiral = True
            logger.info("📝 檢測到補充條件，自動設置 continue_spiral=True")
        
        # 會話管理
        if not session_id:
            session_id = self.dialog.create_session(question, patient_ctx or {})
            logger.info(f"🆕 創建新會話: {session_id}")
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
        
        # ==================== STEP 2: 執行螺旋推理 ====================
        result = await self.spiral.execute_spiral_cycle(
            question=accumulated_question,
            session_id=session_id,
            round_num=round_num
        )
        
        # ==================== STEP 3: 計算收斂度 ====================
        convergence_metrics = self.convergence.calculate_evaluation_metrics(
            session_id=session_id,
            current_result=result
        )
        
        # ==================== STEP 4: 終止條件判斷 ====================
        # ✅ 使用新的終止條件管理器
        if self.stop_criteria:
            try:
                stop_decision_new = self.stop_criteria.evaluate(
                    session_id=session_id,
                    round_num=round_num,
                    metrics=convergence_metrics,
                    history=session.history,
                    user_satisfied=kwargs.get('user_satisfied', False)
                )
                
                # 轉換為原有格式以保持兼容性
                stop_decision = {
                    "should_stop": stop_decision_new.should_stop,
                    "can_save": stop_decision_new.can_save,
                    "treatment_effective": stop_decision_new.treatment_effective,
                    "stop_reason": stop_decision_new.stop_reason,
                    "continue_reason": "" if stop_decision_new.should_stop else "繼續推理",
                    "recommendations": stop_decision_new.recommendations
                }
                logger.info(f"✅ 新終止條件判斷: {stop_decision['should_stop']}")
                
            except Exception as e:
                logger.warning(f"⚠️  終止條件管理器失敗，使用舊方法: {e}")
                import traceback
                traceback.print_exc()
                stop_decision = self.convergence.should_stop(convergence_metrics, round_num)
        else:
            # Fallback 到原有方法
            stop_decision = self.convergence.should_stop(convergence_metrics, round_num)
        
        should_stop = stop_decision["should_stop"]
        can_save = stop_decision.get("can_save", False)
        treatment_effective = stop_decision.get("treatment_effective", False)
        
        # ==================== STEP 5: 補問生成（只在未收斂時） ====================
        gap_questions = []
        if not should_stop and self.gap_asker:
            try:
                symptom_info = result.get("symptom_info", {})
                gap_questions = self.gap_asker.generate_questions(
                    accumulated_symptoms=symptom_info.get("accumulated_symptoms", []),
                    metrics=convergence_metrics,
                    round_num=round_num,
                    max_questions=2
                )
                if gap_questions:
                    logger.info(f"🔍 生成補問: {len(gap_questions)} 個")
                    for idx, q in enumerate(gap_questions, 1):
                        logger.info(f"   {idx}. {q}")
            except Exception as e:
                logger.warning(f"⚠️  補問生成失敗: {e}")
                gap_questions = []
        
        # ==================== STEP 6: 證型轉化檢查 ====================
        pattern_shift_info = {"shifted": False, "new_pattern": None, "reason": "", "original_pattern": ""}
        if round_num >= 2 and self.pattern_shifter:
            try:
                current_diagnosis = result.get("primary", {}).get("diagnosis", "")
                symptom_info = result.get("symptom_info", {})
                
                should_shift, new_pattern, shift_reason = self.pattern_shifter.check_transition(
                    current_pattern=current_diagnosis,
                    new_symptoms=symptom_info.get("new_symptoms", []),
                    accumulated_symptoms=symptom_info.get("accumulated_symptoms", []),
                    round_num=round_num
                )
                
                if should_shift and new_pattern:
                    logger.info(f"🔄 證型轉化: {current_diagnosis} → {new_pattern}")
                    logger.info(f"   原因: {shift_reason}")
                    
                    pattern_shift_info = {
                        "shifted": True,
                        "new_pattern": new_pattern,
                        "reason": shift_reason,
                        "original_pattern": current_diagnosis
                    }
                    
                    # 更新診斷結果
                    if "primary" in result and result["primary"]:
                        result["primary"]["diagnosis"] = new_pattern
                        
                        # 更新輸出文本
                        final_text = result.get("final_text", "")
                        if current_diagnosis and current_diagnosis in final_text:
                            result["final_text"] = final_text.replace(
                                current_diagnosis, 
                                f"{new_pattern}（由{current_diagnosis}轉化）"
                            )
                            
            except Exception as e:
                logger.warning(f"⚠️  證型轉化檢查失敗: {e}")
                import traceback
                traceback.print_exc()
        
        # ==================== STEP 7: 自我審稿（第2輪起） ====================
        review_info = {"passed": True, "issues": [], "revised": False}
        if round_num >= 2 and self.self_reviewer and session.history:
            try:
                previous_output = session.history[-1].get("final_text") if session.history else None
                symptom_info = result.get("symptom_info", {})
                
                review_result = await self.self_reviewer.review(
                    current_output=result.get("final_text", ""),
                    previous_output=previous_output,
                    new_symptoms=symptom_info.get("new_symptoms", []),
                    round_num=round_num
                )
                
                review_info = {
                    "passed": review_result["passed"],
                    "issues": review_result["issues"],
                    "revised": review_result.get("revised_output") is not None
                }
                
                # 如果有修正輸出，使用修正版本
                if review_result.get("revised_output"):
                    result["final_text"] = review_result["revised_output"]
                    logger.info("✏️  使用審稿修正後的輸出")
                
                if not review_result["passed"]:
                    logger.warning(f"⚠️  審稿發現問題: {review_result['issues']}")
                    
            except Exception as e:
                logger.warning(f"⚠️  自我審稿失敗: {e}")
                import traceback
                traceback.print_exc()
        
        # ==================== STEP 8: 儲存提示 ====================
        # 決定是否可以繼續推理
        continue_available = not should_stop and round_num < self.config.spiral.max_rounds
        
        # ✅ 如果有效且達到停止條件，標記為可儲存
        if can_save and should_stop:
            logger.info(f"💾 治療有效，可儲存為 RPCase")
            # 添加儲存提示到結果中
            result["save_prompt"] = {
                "can_save": True,
                "message": "診斷過程已收斂且有效，建議儲存為回饋案例",
                "effectiveness_score": convergence_metrics.get("Final", convergence_metrics.get("overall_convergence", 0))
            }
        else:
            result["save_prompt"] = {
                "can_save": False,
                "message": stop_decision.get("continue_reason", ""),
                "effectiveness_score": 0
            }
        
        # ==================== STEP 9: 記錄到會話歷史 ====================
        self.dialog.record_step(session_id, {
            **result,
            "convergence": convergence_metrics,
            "stop_decision": stop_decision,
            "gap_questions": gap_questions,
            "pattern_shift": pattern_shift_info,
            "review_info": review_info
        })
        
        # ==================== STEP 10: 組裝最終回應 ====================
        processing_time = (datetime.now() - start_time).total_seconds()
        
        response = {
            # 基本信息
            "session_id": session_id,
            "round": round_num,
            "trace_id": trace_id,
            "version": self.version,
            "processing_time": processing_time,
            
            # 收斂與終止
            "converged": should_stop,
            "continue_available": continue_available,
            "convergence_metrics": convergence_metrics,
            "stop_decision": stop_decision,
            
            # 回饋判定
            "treatment_effective": treatment_effective,
            "can_save_to_rpcase": can_save,
            "save_prompt": result.get("save_prompt", {}),
            
            # ✅ 新增欄位
            "gap_questions": gap_questions,           # 補問列表
            "pattern_shift": pattern_shift_info,      # 證型轉化資訊
            "review_info": review_info,               # 審稿資訊
            
            # 診斷結果（展開 result）
            **result
        }
        
        # ==================== STEP 11: 日誌輸出 ====================
        logger.info(f"✅ 診斷完成 [{trace_id}] 耗時: {processing_time:.2f}s")
        logger.info(f"   輪次: {round_num}, 可繼續: {continue_available}")
        logger.info(f"   收斂: {should_stop}, RCI={convergence_metrics.get('RCI', 0):.3f}, Final={convergence_metrics.get('Final', 0):.3f}")
        
        if gap_questions:
            logger.info(f"   補問數量: {len(gap_questions)}")
        
        if pattern_shift_info["shifted"]:
            logger.info(f"   證型轉化: {pattern_shift_info['original_pattern']} → {pattern_shift_info['new_pattern']}")
        
        return response

    def reset_session(self, session_id: str):
        """重置會話"""
        self.dialog.reset_session(session_id)
        self.convergence.clear_history(session_id)
        self.spiral.clear_session_symptoms(session_id)  # ✅ 新增這行
        logger.info(f"🔄 會話重置: {session_id}")

# 全域單例
_engine = SCBREngine()

async def run_spiral_cbr(question: str, **kwargs):
    """公開API入口"""
    return await _engine.diagnose(question, **kwargs)

def get_engine():
    """獲取引擎實例"""
    return _engine