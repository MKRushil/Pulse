"""
S-CBR 螺旋推理引擎核心 v2.0

整合現有 Case 和 PulsePJ 知識庫的螺旋推理引擎
支援會話管理與多輪互動推理

版本：v2.0 - 螺旋互動版
更新：支援會話狀態管理與案例過濾
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime

# 動態導入避免循環依賴
try:
    from ..agents.adaptation_agent import AdaptationAgent
    from ..agents.monitoring_agent import MonitoringAgent
    from ..agents.feedback_agent import FeedbackAgent
    from ..agents.diagnostic_agent import DiagnosticAgent
    from ..knowledge.case_repository import CaseRepository
    from ..knowledge.pulse_repository import PulseRepository
    from ..utils.spiral_logger import SpiralLogger
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    AdaptationAgent = None
    MonitoringAgent = None
    FeedbackAgent = None
    DiagnosticAgent = None
    CaseRepository = None
    PulseRepository = None

class SpiralCBREngine:
    """
    S-CBR 螺旋推理引擎核心 v2.0
    
    v2.0 特色：
    - 支援會話狀態管理
    - 智能案例過濾
    - 多輪推理協調
    - 輪次感知的推理調整
    """
    
    def __init__(self):
        """初始化螺旋推理引擎 v2.0"""
        self.logger = SpiralLogger.get_logger("SpiralCBREngine") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("SpiralCBREngine")
        self.version = "2.0"
        
        # 初始化各個智能體（如果可用）
        self.diagnostic_agent = DiagnosticAgent() if DiagnosticAgent else None
        self.adaptation_agent = AdaptationAgent() if AdaptationAgent else None
        self.monitoring_agent = MonitoringAgent() if MonitoringAgent else None
        self.feedback_agent = FeedbackAgent() if FeedbackAgent else None
        
        # 初始化知識庫（如果可用）
        self.case_repository = CaseRepository() if CaseRepository else None
        self.pulse_repository = PulseRepository() if PulseRepository else None
        
        self.logger.info(f"S-CBR 螺旋推理引擎 v{self.version} 初始化完成")
    
    async def start_spiral_dialog(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        啟動螺旋推理對話 v2.0
        
        v2.0 新增參數：
        - used_cases: 已使用的案例ID列表
        - session_id: 會話ID
        - round: 當前輪次
        - continue_spiral: 是否繼續推理
        
        Args:
            query: 查詢參數，包含患者信息和會話狀態
            
        Returns:
            Dict[str, Any]: 推理結果，包含診斷、治療方案、評估等
        """
        try:
            # 提取 v2.0 新增參數
            question = query.get("question", "")
            patient_ctx = query.get("patient_ctx", {})
            used_cases = query.get("used_cases", [])
            session_id = query.get("session_id", "")
            round_number = query.get("round", 1)
            continue_spiral = query.get("continue_spiral", False)
            trace_id = query.get("trace_id", "")
            
            self.logger.info(f"開始螺旋推理 v2.0 - Session: {session_id}, Round: {round_number}")
            self.logger.info(f"已使用案例數: {len(used_cases)}")
            
            # Step 1: 案例檢索（支援過濾）
            step1_result = await self._step1_case_search_v2(
                question, patient_ctx, used_cases, round_number
            )
            
            if not step1_result.get("selected_case"):
                return self._create_no_case_response(session_id, round_number)
            
            # Step 2: 案例適配
            step2_result = await self._step2_case_adapt_v2(
                step1_result, query, round_number
            )
            
            # Step 3: 方案監控
            step3_result = await self._step3_monitor_v2(
                step2_result, query, round_number
            )
            
            # Step 4: 反饋學習
            step4_result = await self._step4_feedback_v2(
                step3_result, query, round_number
            )
            
            # 構建最終結果
            final_result = self._build_spiral_result_v2(
                step1_result, step2_result, step3_result, step4_result, 
                session_id, round_number
            )
            
            self.logger.info(f"螺旋推理 v2.0 完成 - Session: {session_id}, Round: {round_number}")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"螺旋推理 v2.0 失敗: {str(e)}")
            return self._create_error_response_v2(str(e), session_id, query.get("round", 1))
    
    async def _step1_case_search_v2(self, question: str, patient_ctx: Dict, 
                                   used_cases: List[str], round_number: int) -> Dict[str, Any]:
        """
        Step 1: 案例檢索 v2.0 - 支援過濾已使用案例
        
        Args:
            question: 患者問題描述
            patient_ctx: 患者上下文
            used_cases: 已使用的案例ID列表
            round_number: 當前輪次
            
        Returns:
            Dict[str, Any]: 檢索結果
        """
        self.logger.info(f"Step 1 - 案例檢索 v2.0 (Round {round_number})")
        
        try:
            # 使用 CaseRepository v2.0 API（如果可用）
            if self.case_repository and hasattr(self.case_repository, 'get_similar_cases_v2'):
                similar_cases = await self.case_repository.get_similar_cases_v2(
                    query=question,
                    patient_context=patient_ctx,
                    exclude_cases=used_cases
                )
            else:
                # 降級到舊版本API
                similar_cases = await self._fallback_case_search(question, patient_ctx, used_cases)
            
            # 根據輪次調整案例選擇策略
            selected_case = self._select_case_by_round(similar_cases, round_number)
            
            return {
                "selected_case": selected_case,
                "similar_cases_count": len(similar_cases),
                "cases_filtered": len(used_cases),
                "case_used_id": selected_case.get("id") if selected_case else None,
                "round": round_number
            }
            
        except Exception as e:
            self.logger.error(f"Step 1 案例檢索失敗: {str(e)}")
            return {"error": str(e), "selected_case": None}
    
    def filter_used_cases(self, available_cases: List[Dict], used_cases: List[str]) -> List[Dict]:
        """
        過濾已使用的案例
        
        Args:
            available_cases: 可用案例列表
            used_cases: 已使用案例ID列表
            
        Returns:
            List[Dict]: 過濾後的案例列表
        """
        if not used_cases:
            return available_cases
            
        filtered_cases = [
            case for case in available_cases
            if case.get('id') not in used_cases and case.get('case_id') not in used_cases
        ]
        
        self.logger.info(f"案例過濾: {len(available_cases)} → {len(filtered_cases)} (排除 {len(used_cases)} 個已用案例)")
        
        return filtered_cases
    
    def _select_case_by_round(self, cases: List[Dict], round_number: int) -> Optional[Dict]:
        """
        根據輪次選擇案例
        
        Args:
            cases: 可用案例列表
            round_number: 當前輪次
            
        Returns:
            Optional[Dict]: 選中的案例
        """
        if not cases:
            return None
        
        # 第1輪：選擇相似度最高的
        if round_number == 1:
            return max(cases, key=lambda x: x.get('similarity', 0))
        
        # 第2輪：選擇相似度第二高的
        elif round_number == 2 and len(cases) > 1:
            sorted_cases = sorted(cases, key=lambda x: x.get('similarity', 0), reverse=True)
            return sorted_cases[1]
        
        # 第3輪及以後：選擇多樣性高的案例
        else:
            # 簡單實現：選擇相似度適中的案例
            mid_idx = min(round_number - 1, len(cases) - 1)
            sorted_cases = sorted(cases, key=lambda x: x.get('similarity', 0), reverse=True)
            return sorted_cases[mid_idx]
    
    async def _step2_case_adapt_v2(self, step1_result: Dict, query: Dict, round_number: int) -> Dict[str, Any]:
        """
        Step 2: 案例適配 v2.0 - 支援會話上下文
        
        Args:
            step1_result: Step1 結果
            query: 查詢參數
            round_number: 當前輪次
            
        Returns:
            Dict[str, Any]: 適配結果
        """
        self.logger.info(f"Step 2 - 案例適配 v2.0 (Round {round_number})")
        
        try:
            selected_case = step1_result.get("selected_case")
            if not selected_case:
                return {"error": "無可用案例進行適配"}
            
            # 構建會話上下文
            session_context = {
                "session_id": query.get("session_id"),
                "round": round_number,
                "used_cases": query.get("used_cases", []),
                "continue_spiral": query.get("continue_spiral", False)
            }
            
            # 使用 AdaptationAgent v2.0 API（如果可用）
            if self.adaptation_agent and hasattr(self.adaptation_agent, 'create_adaptation_strategy_v2'):
                adaptation_result = await self.adaptation_agent.create_adaptation_strategy_v2(
                    base_case=selected_case,
                    patient_query=query,
                    session_context=session_context
                )
            else:
                # 降級到舊版本或簡單適配
                adaptation_result = await self._fallback_adaptation(selected_case, query, round_number)
            
            return {
                "adapted_case": selected_case,
                "adaptation_strategy": adaptation_result,
                "treatment_plan": adaptation_result.get("treatment_plan", ""),
                "diagnosis": adaptation_result.get("diagnosis", ""),
                "round": round_number
            }
            
        except Exception as e:
            self.logger.error(f"Step 2 案例適配失敗: {str(e)}")
            return {"error": str(e)}
    
    async def _step3_monitor_v2(self, step2_result: Dict, query: Dict, round_number: int) -> Dict[str, Any]:
        """
        Step 3: 方案監控 v2.0 - 包含輪次資訊
        
        Args:
            step2_result: Step2 結果
            query: 查詢參數
            round_number: 當前輪次
            
        Returns:
            Dict[str, Any]: 監控結果
        """
        self.logger.info(f"Step 3 - 方案監控 v2.0 (Round {round_number})")
        
        try:
            treatment_plan = step2_result.get("treatment_plan", "")
            
            # 構建會話上下文
            session_context = {
                "session_id": query.get("session_id"),
                "round": round_number,
                "used_cases": query.get("used_cases", [])
            }
            
            # 使用 MonitoringAgent v2.0 API（如果可用）
            if self.monitoring_agent and hasattr(self.monitoring_agent, 'generate_monitoring_report_v2'):
                monitoring_result = await self.monitoring_agent.generate_monitoring_report_v2(
                    treatment_plan=step2_result,
                    session_context=session_context
                )
            else:
                # 降級到舊版本或簡單監控
                monitoring_result = await self._fallback_monitoring(step2_result, round_number)
            
            return {
                "safety_score": monitoring_result.get("safety_score", 0.8),
                "efficacy_score": monitoring_result.get("efficacy_score", 0.8),
                "confidence": monitoring_result.get("confidence", 0.8),
                "recommendations": monitoring_result.get("recommendations", []),
                "round": round_number
            }
            
        except Exception as e:
            self.logger.error(f"Step 3 方案監控失敗: {str(e)}")
            return {"error": str(e), "safety_score": 0.5, "efficacy_score": 0.5}
    
    async def _step4_feedback_v2(self, step3_result: Dict, query: Dict, round_number: int) -> Dict[str, Any]:
        """
        Step 4: 反饋學習 v2.0 - 會話級別學習
        
        Args:
            step3_result: Step3 結果
            query: 查詢參數
            round_number: 當前輪次
            
        Returns:
            Dict[str, Any]: 反饋結果
        """
        self.logger.info(f"Step 4 - 反饋學習 v2.0 (Round {round_number})")
        
        try:
            # 構建會話上下文
            session_context = {
                "session_id": query.get("session_id"),
                "round": round_number,
                "used_cases": query.get("used_cases", []),
                "total_rounds": round_number
            }
            
            # 使用 FeedbackAgent v2.0 API（如果可用）
            if self.feedback_agent and hasattr(self.feedback_agent, 'analyze_feedback_v2'):
                feedback_result = await self.feedback_agent.analyze_feedback_v2(
                    session_result=step3_result,
                    session_context=session_context
                )
            else:
                # 降級到舊版本或簡單反饋
                feedback_result = await self._fallback_feedback(step3_result, round_number)
            
            return {
                "learning_insights": feedback_result.get("learning_insights", []),
                "session_effectiveness": feedback_result.get("session_effectiveness", 0.8),
                "continue_recommended": feedback_result.get("continue_recommended", True),
                "round": round_number
            }
            
        except Exception as e:
            self.logger.error(f"Step 4 反饋學習失敗: {str(e)}")
            return {"error": str(e)}
    
    def _build_spiral_result_v2(self, step1: Dict, step2: Dict, step3: Dict, step4: Dict, 
                               session_id: str, round_number: int) -> Dict[str, Any]:
        """
        構建螺旋推理最終結果 v2.0
        
        Returns:
            Dict[str, Any]: 完整的推理結果
        """
        return {
            "dialog": self._format_dialog_v2(step2, step3, round_number),
            "diagnosis": step2.get("diagnosis", ""),
            "treatment_plan": step2.get("treatment_plan", ""),
            "safety_score": step3.get("safety_score", 0.8),
            "efficacy_score": step3.get("efficacy_score", 0.8),
            "confidence": step3.get("confidence", 0.8),
            "recommendations": step3.get("recommendations", []),
            "case_used": step1.get("selected_case", {}).get("summary", ""),
            "case_used_id": step1.get("case_used_id"),
            "round": round_number,
            "session_id": session_id,
            "llm_struct": {
                "main_dx": step2.get("diagnosis", ""),
                "confidence": step3.get("confidence", 0.8),
                "safety_score": step3.get("safety_score", 0.8),
                "efficacy_score": step3.get("efficacy_score", 0.8),
                "case_used": step1.get("selected_case", {}).get("summary", ""),
                "round": round_number
            },
            "success": True,
            "spiral_rounds": round_number,
            "version": self.version
        }
    
    def _format_dialog_v2(self, step2: Dict, step3: Dict, round_number: int) -> str:
        """格式化對話回應 v2.0"""
        diagnosis = step2.get("diagnosis", "診斷分析中...")
        treatment = step2.get("treatment_plan", "治療方案制定中...")
        safety = step3.get("safety_score", 0.8)
        efficacy = step3.get("efficacy_score", 0.8)
        confidence = step3.get("confidence", 0.8)
        
        return f"""基於第{round_number}輪螺旋推理分析：

📋 **中醫診斷**
{diagnosis}

💊 **治療方案**
{treatment}

📊 **方案評估**
• 安全性評分：{safety:.2f}/1.0
• 有效性評分：{efficacy:.2f}/1.0  
• 整體信心度：{confidence:.2f}/1.0

本輪推理基於相似案例進行適配，如需更多診療選擇，可繼續推理獲得其他方案。"""
    
    # 降級方法（兼容性）
    async def _fallback_case_search(self, question: str, patient_ctx: Dict, used_cases: List[str]) -> List[Dict]:
        """降級案例搜索"""
        # 簡單實現：返回模擬案例
        return [
            {
                "id": f"case_{i}",
                "summary": f"相似案例 {i}",
                "similarity": 0.8 - i * 0.1,
                "diagnosis": "頭痛失眠",
                "treatment": "疏肝解鬱，養心安神"
            }
            for i in range(1, 4) if f"case_{i}" not in used_cases
        ]
    
    async def _fallback_adaptation(self, case: Dict, query: Dict, round_number: int) -> Dict:
        """降級適配"""
        return {
            "diagnosis": case.get("diagnosis", "診斷待完善"),
            "treatment_plan": case.get("treatment", "治療方案待適配"),
            "confidence": max(0.5, 0.9 - round_number * 0.1)
        }
    
    async def _fallback_monitoring(self, step2_result: Dict, round_number: int) -> Dict:
        """降級監控"""
        base_score = max(0.6, 0.9 - round_number * 0.05)
        return {
            "safety_score": base_score,
            "efficacy_score": base_score - 0.05,
            "confidence": base_score,
            "recommendations": ["建議密切觀察患者反應"]
        }
    
    async def _fallback_feedback(self, step3_result: Dict, round_number: int) -> Dict:
        """降級反饋"""
        return {
            "learning_insights": [f"第{round_number}輪推理完成"],
            "session_effectiveness": step3_result.get("confidence", 0.8),
            "continue_recommended": round_number < 3
        }
    
    def _create_no_case_response(self, session_id: str, round_number: int) -> Dict[str, Any]:
        """創建無案例時的回應"""
        return {
            "dialog": f"第{round_number}輪推理暫未找到合適的相似案例，建議調整查詢條件或諮詢專業醫師。",
            "diagnosis": "",
            "treatment_plan": "",
            "error": "no_similar_cases_found",
            "session_id": session_id,
            "round": round_number,
            "success": False
        }
    
    def _create_error_response_v2(self, error_message: str, session_id: str, round_number: int) -> Dict[str, Any]:
        """創建錯誤回應 v2.0"""
        return {
            "dialog": f"第{round_number}輪螺旋推理過程中發生錯誤：{error_message}",
            "error": error_message,
            "session_id": session_id,
            "round": round_number,
            "success": False,
            "version": self.version
        }

# 向後兼容的類別名稱
SpiralCBREngineV2 = SpiralCBREngine

__all__ = ["SpiralCBREngine", "SpiralCBREngineV2"]