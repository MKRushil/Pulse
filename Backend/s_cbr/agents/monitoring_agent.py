"""
監控智能體 v2.0

負責監控治療方案的安全性與有效性
支援輪次感知的風險評估與建議生成

版本：v2.0 - 螺旋互動版
更新：包含輪次資訊與會話級別監控
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..utils.api_manager import SCBRAPIManager
    from ..knowledge.case_repository import CaseRepository
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SCBRAPIManager = None
    CaseRepository = None

class MonitoringAgent:
    """
    中醫監控智能體 v2.0
    
    v2.0 特色：
    - 輪次感知的安全性評估
    - 會話級別的療效監控
    - 多輪推理風險累積分析
    - 動態建議生成
    """
    
    def __init__(self):
        """初始化監控智能體 v2.0"""
        self.logger = SpiralLogger.get_logger("MonitoringAgent") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("MonitoringAgent")
        self.version = "2.0"
        
        # 初始化相關組件
        self.api_manager = SCBRAPIManager() if SCBRAPIManager else None
        self.case_repository = CaseRepository() if CaseRepository else None
        
        # v2.0 監控參數
        self.safety_thresholds = {
            "high_risk": 0.7,
            "medium_risk": 0.4,
            "low_risk": 0.2
        }
        
        self.efficacy_benchmarks = {
            "excellent": 0.8,
            "good": 0.6,
            "acceptable": 0.4,
            "poor": 0.2
        }
        
        self.logger.info(f"中醫監控智能體 v{self.version} 初始化完成")
    
    async def generate_monitoring_report_v2(self, 
                                          treatment_plan: Dict[str, Any],
                                          session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成監控報告 v2.0 - 包含輪次資訊
        
        Args:
            treatment_plan: 治療方案（來自適配結果）
            session_context: 會話上下文（session_id, round, used_cases等）
            
        Returns:
            Dict[str, Any]: 監控報告結果
        """
        try:
            session_id = session_context.get("session_id", "")
            round_number = session_context.get("round", 1)
            used_cases_count = len(session_context.get("used_cases", []))
            
            self.logger.info(f"開始監控評估 v2.0 - Session: {session_id}, Round: {round_number}")
            
            # 1. 安全性評估（輪次感知）
            safety_assessment = await self._evaluate_safety_v2(treatment_plan, session_context)
            
            # 2. 有效性評估（會話級別）
            efficacy_assessment = await self._evaluate_efficacy_v2(treatment_plan, session_context)
            
            # 3. 風險累積分析（多輪推理）
            cumulative_risk = await self._analyze_cumulative_risk_v2(treatment_plan, session_context)
            
            # 4. 療效預測（基於輪次歷史）
            efficacy_prediction = await self._predict_treatment_efficacy_v2(treatment_plan, session_context)
            
            # 5. 建議生成（動態調整）
            recommendations = await self._generate_recommendations_v2(
                safety_assessment, efficacy_assessment, session_context
            )
            
            # 6. 繼續推理建議
            continue_recommendation = await self._assess_continue_recommendation_v2(
                safety_assessment, efficacy_assessment, session_context
            )
            
            # 7. 整體信心度計算
            overall_confidence = await self._calculate_overall_confidence_v2(
                safety_assessment, efficacy_assessment, session_context
            )
            
            # 構建監控報告
            monitoring_report = {
                "safety_score": safety_assessment["safety_score"],
                "efficacy_score": efficacy_assessment["efficacy_score"],
                "confidence": overall_confidence,
                "cumulative_risk": cumulative_risk,
                "efficacy_prediction": efficacy_prediction,
                "recommendations": recommendations,
                "continue_recommended": continue_recommendation["recommended"],
                "continue_reason": continue_recommendation["reason"],
                "safety_details": safety_assessment["details"],
                "efficacy_details": efficacy_assessment["details"],
                "round": round_number,
                "session_id": session_id,
                "used_cases_count": used_cases_count,
                "assessment_timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            self.logger.info(f"監控評估 v2.0 完成 - 安全性: {safety_assessment['safety_score']:.3f}, "
                          f"有效性: {efficacy_assessment['efficacy_score']:.3f}, "
                          f"信心度: {overall_confidence:.3f}")
            
            return monitoring_report
            
        except Exception as e:
            self.logger.error(f"監控評估 v2.0 失敗: {str(e)}")
            return await self._create_fallback_monitoring_v2(treatment_plan, session_context)
    
    async def _evaluate_safety_v2(self, treatment_plan: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        評估治療安全性 v2.0 - 輪次感知評估
        
        Returns:
            Dict[str, Any]: 安全性評估結果
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        # 基礎安全性分析
        base_safety = await self._analyze_base_safety(treatment_plan)
        
        # v2.0: 輪次風險因素
        round_risk_factor = self._calculate_round_risk_factor(round_number)
        
        # v2.0: 案例多樣性風險
        case_diversity_risk = self._calculate_case_diversity_risk(used_cases_count)
        
        # v2.0: 適配風險
        adaptation_risk = self._calculate_adaptation_risk(treatment_plan, round_number)
        
        # 計算綜合安全性評分
        safety_score = max(0.1, base_safety - round_risk_factor - case_diversity_risk - adaptation_risk)
        
        # 安全性等級判定
        safety_level = self._determine_safety_level(safety_score)
        
        # 安全性詳細信息
        safety_details = {
            "base_safety": base_safety,
            "round_risk_factor": round_risk_factor,
            "case_diversity_risk": case_diversity_risk,
            "adaptation_risk": adaptation_risk,
            "safety_level": safety_level,
            "risk_factors": await self._identify_safety_risk_factors(treatment_plan, session_context)
        }
        
        return {
            "safety_score": min(safety_score, 1.0),
            "safety_level": safety_level,
            "details": safety_details,
            "round": round_number
        }
    
    async def _evaluate_efficacy_v2(self, treatment_plan: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        評估治療有效性 v2.0 - 會話級別評估
        
        Returns:
            Dict[str, Any]: 有效性評估結果
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        # 基礎有效性分析
        base_efficacy = await self._analyze_base_efficacy(treatment_plan)
        
        # v2.0: 輪次增強因素（多案例集成可能提高有效性）
        round_enhancement = self._calculate_round_enhancement(round_number, used_cases_count)
        
        # v2.0: 適配質量加成
        adaptation_quality_bonus = self._calculate_adaptation_quality_bonus(treatment_plan, round_number)
        
        # v2.0: 會話歷史調整
        session_history_adjustment = await self._calculate_session_history_adjustment(session_context)
        
        # 計算綜合有效性評分
        efficacy_score = min(1.0, base_efficacy + round_enhancement + adaptation_quality_bonus + session_history_adjustment)
        
        # 有效性等級判定
        efficacy_level = self._determine_efficacy_level(efficacy_score)
        
        # 有效性詳細信息
        efficacy_details = {
            "base_efficacy": base_efficacy,
            "round_enhancement": round_enhancement,
            "adaptation_quality_bonus": adaptation_quality_bonus,
            "session_history_adjustment": session_history_adjustment,
            "efficacy_level": efficacy_level,
            "enhancement_factors": await self._identify_efficacy_enhancement_factors(treatment_plan, session_context)
        }
        
        return {
            "efficacy_score": efficacy_score,
            "efficacy_level": efficacy_level,
            "details": efficacy_details,
            "round": round_number
        }
    
    async def _analyze_cumulative_risk_v2(self, treatment_plan: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        分析累積風險 v2.0 - 多輪推理風險累積
        
        Returns:
            Dict[str, Any]: 累積風險分析
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        # 基礎累積風險
        base_cumulative_risk = min(round_number * 0.05, 0.25)
        
        # 案例多樣性風險累積
        case_diversity_cumulative = min(used_cases_count * 0.03, 0.15)
        
        # 適配複雜度累積
        adaptation_complexity = treatment_plan.get("adaptation_weight", 0.5) * round_number * 0.02
        
        # 總累積風險
        total_cumulative_risk = min(base_cumulative_risk + case_diversity_cumulative + adaptation_complexity, 0.5)
        
        # 風險趨勢分析
        risk_trend = "上升" if round_number > 2 else "穩定" if round_number == 2 else "初始"
        
        return {
            "total_cumulative_risk": total_cumulative_risk,
            "base_cumulative_risk": base_cumulative_risk,
            "case_diversity_cumulative": case_diversity_cumulative,
            "adaptation_complexity": adaptation_complexity,
            "risk_trend": risk_trend,
            "risk_threshold_reached": total_cumulative_risk > 0.3,
            "round": round_number
        }
    
    async def _predict_treatment_efficacy_v2(self, treatment_plan: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        預測治療療效 v2.0 - 基於輪次歷史
        
        Returns:
            Dict[str, Any]: 療效預測結果
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        # 基礎療效預測
        base_prediction = 0.75
        
        # 輪次修正（多輪推理可能提高精確度）
        round_correction = min(round_number * 0.05, 0.15)
        
        # 案例豐富度加成
        case_richness_bonus = min(used_cases_count * 0.03, 0.1)
        
        # 適配品質影響
        adaptation_impact = treatment_plan.get("success_rate", 0.8) * 0.2
        
        # 最終療效預測
        predicted_efficacy = min(base_prediction + round_correction + case_richness_bonus + adaptation_impact, 0.95)
        
        # 預測信心度
        prediction_confidence = min(0.6 + round_number * 0.1 + used_cases_count * 0.05, 0.9)
        
        # 療效時間預估
        predicted_timeline = self._estimate_treatment_timeline(treatment_plan, round_number)
        
        return {
            "predicted_efficacy": predicted_efficacy,
            "prediction_confidence": prediction_confidence,
            "predicted_timeline": predicted_timeline,
            "factors": {
                "base_prediction": base_prediction,
                "round_correction": round_correction,
                "case_richness_bonus": case_richness_bonus,
                "adaptation_impact": adaptation_impact
            },
            "round": round_number
        }
    
    async def _generate_recommendations_v2(self, safety_assessment: Dict, 
                                         efficacy_assessment: Dict, 
                                         session_context: Dict) -> List[str]:
        """
        生成監控建議 v2.0 - 動態調整建議
        
        Returns:
            List[str]: 監控建議列表
        """
        round_number = session_context.get("round", 1)
        safety_score = safety_assessment["safety_score"]
        efficacy_score = efficacy_assessment["efficacy_score"]
        safety_level = safety_assessment["safety_level"]
        efficacy_level = efficacy_assessment["efficacy_level"]
        
        recommendations = []
        
        # 基於輪次的基本建議
        recommendations.append(f"第{round_number}輪螺旋推理監控建議")
        
        # 安全性相關建議
        if safety_level == "高風險":
            recommendations.extend([
                "⚠️ 治療方案安全風險較高，建議諮詢專業中醫師",
                "🔍 密切監控治療過程中的不良反應",
                "📞 如有異常症狀請立即停止治療並就醫"
            ])
        elif safety_level == "中風險":
            recommendations.extend([
                "⚡ 治療方案需要適度關注安全性",
                "📋 建議記錄治療反應，定期評估"
            ])
        else:
            recommendations.append("✅ 治療方案安全性良好")
        
        # 有效性相關建議
        if efficacy_level == "優秀":
            recommendations.append("🌟 預期治療效果很好，建議按方案執行")
        elif efficacy_level == "良好":
            recommendations.append("👍 預期治療效果較好，可繼續執行")
        elif efficacy_level == "可接受":
            recommendations.extend([
                "📊 治療效果可能一般，建議評估是否需要調整",
                "🔄 考慮進行下一輪螺旋推理以優化方案"
            ])
        else:
            recommendations.extend([
                "⚠️ 治療效果可能不佳，建議重新評估",
                "🔄 建議進行下一輪推理或諮詢專業醫師"
            ])
        
        # 輪次特定建議
        if round_number >= 3:
            recommendations.append("🎯 已進行多輪推理，建議綜合評估最佳方案")
        
        if round_number >= 5:
            recommendations.append("⏳ 推理輪次較多，建議確定最終治療方案")
        
        return recommendations
    
    async def _assess_continue_recommendation_v2(self, safety_assessment: Dict, 
                                               efficacy_assessment: Dict,
                                               session_context: Dict) -> Dict[str, Any]:
        """
        評估繼續推理建議 v2.0
        
        Returns:
            Dict[str, Any]: 繼續推理建議
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        safety_score = safety_assessment["safety_score"]
        efficacy_score = efficacy_assessment["efficacy_score"]
        
        # 繼續推理的條件評估
        conditions = {
            "safety_acceptable": safety_score >= 0.4,
            "efficacy_improvable": efficacy_score < 0.8,
            "rounds_reasonable": round_number < 5,
            "cases_available": used_cases_count < 8,
            "overall_benefit": (safety_score + efficacy_score) / 2 < 0.85
        }
        
        # 計算繼續推理的綜合評分
        continue_score = sum(conditions.values()) / len(conditions)
        
        # 決定是否建議繼續
        should_continue = continue_score >= 0.6 and conditions["safety_acceptable"]
        
        # 生成建議原因
        if should_continue:
            if efficacy_score < 0.6:
                reason = "當前療效有待提升，建議繼續推理尋找更好方案"
            elif round_number <= 2:
                reason = "推理輪次較少，可以嘗試更多診療選擇"
            else:
                reason = "方案仍有優化空間，建議進行下一輪推理"
        else:
            if not conditions["safety_acceptable"]:
                reason = "安全風險較高，不建議繼續推理"
            elif round_number >= 5:
                reason = "已進行多輪推理，建議確定當前最佳方案"
            elif used_cases_count >= 8:
                reason = "已使用較多案例，建議從現有方案中選擇"
            else:
                reason = "當前方案較為滿意，可以考慮採用"
        
        return {
            "recommended": should_continue,
            "reason": reason,
            "continue_score": continue_score,
            "conditions": conditions,
            "round": round_number
        }
    
    async def _calculate_overall_confidence_v2(self, safety_assessment: Dict, 
                                             efficacy_assessment: Dict,
                                             session_context: Dict) -> float:
        """
        計算整體信心度 v2.0
        
        Returns:
            float: 整體信心度 (0.0-1.0)
        """
        round_number = session_context.get("round", 1)
        safety_score = safety_assessment["safety_score"]
        efficacy_score = efficacy_assessment["efficacy_score"]
        
        # 基礎信心度（安全性與有效性的權重平均）
        base_confidence = safety_score * 0.6 + efficacy_score * 0.4
        
        # 輪次調整（適度推理可提高信心度）
        if round_number == 1:
            round_adjustment = 0.0
        elif round_number <= 3:
            round_adjustment = round_number * 0.05
        else:
            round_adjustment = 0.15 - (round_number - 3) * 0.03
        
        # 安全-有效性平衡加成
        balance_bonus = 0.0
        if abs(safety_score - efficacy_score) < 0.2:
            balance_bonus = 0.05
        
        # 最終信心度
        overall_confidence = min(base_confidence + round_adjustment + balance_bonus, 1.0)
        
        return max(overall_confidence, 0.3)
    
    # 輔助方法實現
    async def _analyze_base_safety(self, treatment_plan: Dict) -> float:
        """分析基礎安全性"""
        # 簡化實現
        risk_assessment = treatment_plan.get("risk_assessment", {})
        base_risk = risk_assessment.get("total_risk_score", 0.3)
        return max(0.4, 1.0 - base_risk)
    
    def _calculate_round_risk_factor(self, round_number: int) -> float:
        """計算輪次風險因素"""
        return min(round_number * 0.02, 0.1)
    
    def _calculate_case_diversity_risk(self, used_cases_count: int) -> float:
        """計算案例多樣性風險"""
        return min(used_cases_count * 0.01, 0.05)
    
    def _calculate_adaptation_risk(self, treatment_plan: Dict, round_number: int) -> float:
        """計算適配風險"""
        adaptation_weight = treatment_plan.get("adaptation_weight", 0.5)
        return adaptation_weight * round_number * 0.01
    
    def _determine_safety_level(self, safety_score: float) -> str:
        """判定安全性等級"""
        if safety_score >= 0.7:
            return "低風險"
        elif safety_score >= 0.4:
            return "中風險"
        else:
            return "高風險"
    
    async def _identify_safety_risk_factors(self, treatment_plan: Dict, session_context: Dict) -> List[str]:
        """識別安全風險因素"""
        factors = []
        round_number = session_context.get("round", 1)
        
        if round_number >= 3:
            factors.append("多輪推理累積風險")
        
        if treatment_plan.get("adaptation_weight", 0.5) > 0.7:
            factors.append("高強度適配風險")
        
        if len(session_context.get("used_cases", [])) >= 5:
            factors.append("案例多樣性風險")
        
        return factors if factors else ["無明顯風險因素"]
    
    async def _analyze_base_efficacy(self, treatment_plan: Dict) -> float:
        """分析基礎有效性"""
        # 簡化實現
        success_rate = treatment_plan.get("success_rate", 0.8)
        confidence = treatment_plan.get("confidence", 0.8)
        return (success_rate + confidence) / 2
    
    def _calculate_round_enhancement(self, round_number: int, used_cases_count: int) -> float:
        """計算輪次增強因素"""
        base_enhancement = min(round_number * 0.03, 0.1)
        case_diversity_enhancement = min(used_cases_count * 0.02, 0.08)
        return base_enhancement + case_diversity_enhancement
    
    def _calculate_adaptation_quality_bonus(self, treatment_plan: Dict, round_number: int) -> float:
        """計算適配質量加成"""
        confidence = treatment_plan.get("confidence", 0.8)
        return confidence * 0.1 * min(round_number / 3, 1.0)
    
    async def _calculate_session_history_adjustment(self, session_context: Dict) -> float:
        """計算會話歷史調整"""
        # 簡化實現
        used_cases_count = len(session_context.get("used_cases", []))
        return min(used_cases_count * 0.01, 0.05)
    
    def _determine_efficacy_level(self, efficacy_score: float) -> str:
        """判定有效性等級"""
        if efficacy_score >= 0.8:
            return "優秀"
        elif efficacy_score >= 0.6:
            return "良好"
        elif efficacy_score >= 0.4:
            return "可接受"
        else:
            return "待改善"
    
    async def _identify_efficacy_enhancement_factors(self, treatment_plan: Dict, session_context: Dict) -> List[str]:
        """識別有效性增強因素"""
        factors = []
        
        if session_context.get("round", 1) > 1:
            factors.append("多輪推理優化")
        
        if len(session_context.get("used_cases", [])) > 2:
            factors.append("案例集成增強")
        
        if treatment_plan.get("confidence", 0.8) > 0.8:
            factors.append("高信心度適配")
        
        return factors if factors else ["基礎療效因素"]
    
    def _estimate_treatment_timeline(self, treatment_plan: Dict, round_number: int) -> str:
        """估算治療時程"""
        base_timeline = "2-4週"
        
        if round_number > 2:
            return "1-3週"  # 多輪推理可能縮短見效時間
        else:
            return base_timeline
    
    async def _create_fallback_monitoring_v2(self, treatment_plan: Dict, session_context: Dict) -> Dict[str, Any]:
        """創建降級監控報告 v2.0"""
        round_number = session_context.get("round", 1)
        
        return {
            "safety_score": 0.7,
            "efficacy_score": 0.7,
            "confidence": 0.6,
            "recommendations": [f"第{round_number}輪基礎監控建議", "請諮詢專業醫師"],
            "continue_recommended": round_number < 3,
            "continue_reason": f"第{round_number}輪降級監控",
            "round": round_number,
            "session_id": session_context.get("session_id", "fallback"),
            "fallback": True,
            "version": self.version
        }
    
    # 向後兼容方法（v1.0）
    async def evaluate_safety(self, treatment_plan: Dict, **kwargs) -> float:
        """向後兼容的安全性評估"""
        session_context = {"round": 1, "session_id": "legacy", "used_cases": []}
        result = await self._evaluate_safety_v2(treatment_plan, session_context)
        return result["safety_score"]
    
    async def evaluate_efficacy(self, treatment_plan: Dict, **kwargs) -> float:
        """向後兼容的有效性評估"""
        session_context = {"round": 1, "session_id": "legacy", "used_cases": []}
        result = await self._evaluate_efficacy_v2(treatment_plan, session_context)
        return result["efficacy_score"]
    
    async def generate_monitoring_report(self, treatment_plan: Dict, **kwargs) -> Dict[str, Any]:
        """向後兼容的監控報告生成"""
        session_context = {"round": 1, "session_id": "legacy", "used_cases": []}
        return await self.generate_monitoring_report_v2(treatment_plan, session_context)

# 向後兼容的類別名稱
MonitoringAgentV2 = MonitoringAgent

__all__ = ["MonitoringAgent", "MonitoringAgentV2"]