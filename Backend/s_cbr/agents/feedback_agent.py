"""
反饋學習智能體 v2.0

負責分析會話結果並進行知識學習與更新
支援會話級別的反饋分析與知識庫優化

版本：v2.0 - 螺旋互動版
更新：會話級別學習記錄與知識庫整合
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..knowledge.spiral_memory import SpiralMemory
    from ..knowledge.case_repository import CaseRepository
    from ..utils.api_manager import SCBRAPIManager
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SpiralMemory = None
    CaseRepository = None
    SCBRAPIManager = None

class FeedbackAgent:
    """
    中醫反饋學習智能體 v2.0
    
    v2.0 特色：
    - 會話級別的反饋分析
    - 多輪推理學習記錄
    - 知識庫動態更新
    - 推理效果評估與優化
    """
    
    def __init__(self):
        """初始化反饋學習智能體 v2.0"""
        self.logger = SpiralLogger.get_logger("FeedbackAgent") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("FeedbackAgent")
        self.version = "2.0"
        
        # 初始化相關組件
        self.spiral_memory = SpiralMemory() if SpiralMemory else None
        self.case_repository = CaseRepository() if CaseRepository else None
        self.api_manager = SCBRAPIManager() if SCBRAPIManager else None
        
        # v2.0 學習參數
        self.learning_weights = {
            "session_effectiveness": 0.3,
            "case_usage_quality": 0.25,
            "adaptation_success": 0.2,
            "safety_compliance": 0.15,
            "user_satisfaction": 0.1
        }
        
        self.effectiveness_thresholds = {
            "excellent": 0.85,
            "good": 0.7,
            "acceptable": 0.55,
            "poor": 0.4
        }
        
        self.logger.info(f"中醫反饋學習智能體 v{self.version} 初始化完成")
    
    async def analyze_feedback_v2(self, 
                                session_result: Dict[str, Any],
                                session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析反饋 v2.0 - 會話級別學習
        
        Args:
            session_result: 當前會話推理結果
            session_context: 會話上下文（session_id, round, used_cases等）
            
        Returns:
            Dict[str, Any]: 反饋分析結果
        """
        try:
            session_id = session_context.get("session_id", "")
            round_number = session_context.get("round", 1)
            used_cases = session_context.get("used_cases", [])
            total_rounds = session_context.get("total_rounds", round_number)
            
            self.logger.info(f"開始反饋分析 v2.0 - Session: {session_id}, Round: {round_number}")
            
            # 1. 會話效果評估
            session_effectiveness = await self._evaluate_session_effectiveness_v2(
                session_result, session_context
            )
            
            # 2. 案例使用品質分析
            case_usage_quality = await self._analyze_case_usage_quality_v2(
                used_cases, session_result, session_context
            )
            
            # 3. 適配成功度評估
            adaptation_success = await self._evaluate_adaptation_success_v2(
                session_result, session_context
            )
            
            # 4. 安全性合規度檢查
            safety_compliance = await self._check_safety_compliance_v2(
                session_result, session_context
            )
            
            # 5. 學習洞察生成
            learning_insights = await self._generate_learning_insights_v2(
                session_effectiveness, case_usage_quality, adaptation_success, session_context
            )
            
            # 6. 知識庫更新建議
            knowledge_update_recommendations = await self._recommend_knowledge_updates_v2(
                session_result, session_context
            )
            
            # 7. 繼續推理建議
            continue_recommendation = await self._generate_continue_recommendation_v2(
                session_effectiveness, session_context
            )
            
            # 8. 會話學習記錄
            session_learning = await self._create_session_learning_record_v2(
                session_result, session_context, session_effectiveness
            )
            
            # 構建反饋分析結果
            feedback_result = {
                "session_effectiveness": session_effectiveness["effectiveness_score"],
                "effectiveness_level": session_effectiveness["effectiveness_level"],
                "case_usage_quality": case_usage_quality,
                "adaptation_success": adaptation_success,
                "safety_compliance": safety_compliance,
                "learning_insights": learning_insights,
                "knowledge_update_recommendations": knowledge_update_recommendations,
                "continue_recommended": continue_recommendation["recommended"],
                "continue_confidence": continue_recommendation["confidence"],
                "session_learning": session_learning,
                "overall_feedback_score": await self._calculate_overall_feedback_score(
                    session_effectiveness, case_usage_quality, adaptation_success, safety_compliance
                ),
                "round": round_number,
                "session_id": session_id,
                "total_rounds": total_rounds,
                "used_cases_count": len(used_cases),
                "analysis_timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 異步更新知識庫
            await self._update_knowledge_base_async_v2(session_learning, knowledge_update_recommendations)
            
            self.logger.info(f"反饋分析 v2.0 完成 - 會話效果: {session_effectiveness['effectiveness_score']:.3f}, "
                          f"整體評分: {feedback_result['overall_feedback_score']:.3f}")
            
            return feedback_result
            
        except Exception as e:
            self.logger.error(f"反饋分析 v2.0 失敗: {str(e)}")
            return await self._create_fallback_feedback_v2(session_result, session_context)
    
    async def _evaluate_session_effectiveness_v2(self, session_result: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        評估會話效果 v2.0
        
        Returns:
            Dict[str, Any]: 會話效果評估結果
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        # 基礎效果指標
        safety_score = session_result.get("safety_score", 0.7)
        efficacy_score = session_result.get("efficacy_score", 0.7)
        confidence = session_result.get("confidence", 0.7)
        
        # v2.0: 會話級別效果因素
        round_efficiency = self._calculate_round_efficiency(round_number, used_cases_count)
        case_utilization = self._calculate_case_utilization_effectiveness(used_cases_count, round_number)
        convergence_quality = self._assess_convergence_quality(session_result, session_context)
        
        # 計算綜合效果評分
        effectiveness_score = (
            safety_score * self.learning_weights["safety_compliance"] +
            efficacy_score * 0.3 +
            confidence * 0.2 +
            round_efficiency * 0.15 +
            case_utilization * 0.15 +
            convergence_quality * 0.2
        )
        
        # 效果等級判定
        effectiveness_level = self._determine_effectiveness_level(effectiveness_score)
        
        # 效果詳細分析
        effectiveness_details = {
            "safety_score": safety_score,
            "efficacy_score": efficacy_score,
            "confidence": confidence,
            "round_efficiency": round_efficiency,
            "case_utilization": case_utilization,
            "convergence_quality": convergence_quality,
            "improvement_areas": await self._identify_improvement_areas_v2(session_result, session_context)
        }
        
        return {
            "effectiveness_score": min(effectiveness_score, 1.0),
            "effectiveness_level": effectiveness_level,
            "details": effectiveness_details,
            "round": round_number
        }
    
    async def _analyze_case_usage_quality_v2(self, used_cases: List[str], 
                                           session_result: Dict, 
                                           session_context: Dict) -> Dict[str, Any]:
        """
        分析案例使用品質 v2.0
        
        Returns:
            Dict[str, Any]: 案例使用品質分析結果
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(used_cases)
        
        # 基礎品質指標
        case_diversity_score = min(used_cases_count / 5, 1.0)  # 案例多樣性
        case_relevance_score = session_result.get("confidence", 0.7)  # 案例相關性
        case_efficiency_score = self._calculate_case_efficiency(used_cases_count, round_number)
        
        # v2.0: 案例使用模式分析
        usage_pattern = await self._analyze_case_usage_pattern_v2(used_cases, session_context)
        
        # 案例品質評估
        case_quality_assessment = await self._assess_individual_case_quality_v2(used_cases, session_result)
        
        # 計算綜合品質評分
        overall_quality = (
            case_diversity_score * 0.3 +
            case_relevance_score * 0.3 +
            case_efficiency_score * 0.2 +
            usage_pattern["pattern_score"] * 0.2
        )
        
        return {
            "overall_quality": overall_quality,
            "case_diversity_score": case_diversity_score,
            "case_relevance_score": case_relevance_score,
            "case_efficiency_score": case_efficiency_score,
            "usage_pattern": usage_pattern,
            "case_quality_assessment": case_quality_assessment,
            "used_cases_count": used_cases_count,
            "round": round_number
        }
    
    async def _evaluate_adaptation_success_v2(self, session_result: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        評估適配成功度 v2.0
        
        Returns:
            Dict[str, Any]: 適配成功度評估結果
        """
        round_number = session_context.get("round", 1)
        
        # 適配成功度指標
        adaptation_confidence = session_result.get("confidence", 0.7)
        safety_maintenance = session_result.get("safety_score", 0.7)
        efficacy_enhancement = session_result.get("efficacy_score", 0.7)
        
        # v2.0: 多輪適配效果分析
        adaptation_progression = self._analyze_adaptation_progression(session_context)
        adaptation_stability = self._assess_adaptation_stability(session_result, round_number)
        
        # 計算適配成功度
        adaptation_success_score = (
            adaptation_confidence * 0.3 +
            safety_maintenance * 0.25 +
            efficacy_enhancement * 0.25 +
            adaptation_progression * 0.1 +
            adaptation_stability * 0.1
        )
        
        # 成功度等級
        if adaptation_success_score >= 0.8:
            success_level = "優秀"
        elif adaptation_success_score >= 0.65:
            success_level = "良好"
        elif adaptation_success_score >= 0.5:
            success_level = "可接受"
        else:
            success_level = "需改善"
        
        return {
            "adaptation_success_score": adaptation_success_score,
            "success_level": success_level,
            "adaptation_confidence": adaptation_confidence,
            "safety_maintenance": safety_maintenance,
            "efficacy_enhancement": efficacy_enhancement,
            "adaptation_progression": adaptation_progression,
            "adaptation_stability": adaptation_stability,
            "round": round_number
        }
    
    async def _check_safety_compliance_v2(self, session_result: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        檢查安全性合規度 v2.0
        
        Returns:
            Dict[str, Any]: 安全性合規度檢查結果
        """
        round_number = session_context.get("round", 1)
        
        # 安全性指標
        safety_score = session_result.get("safety_score", 0.7)
        risk_level = "低" if safety_score >= 0.7 else "中" if safety_score >= 0.4 else "高"
        
        # v2.0: 多輪安全性追蹤
        cumulative_safety = await self._assess_cumulative_safety_v2(session_context)
        safety_trend = await self._analyze_safety_trend_v2(session_context)
        
        # 合規度評估
        compliance_score = min(safety_score + cumulative_safety * 0.2, 1.0)
        
        # 合規等級
        if compliance_score >= 0.8:
            compliance_level = "優秀"
        elif compliance_score >= 0.6:
            compliance_level = "良好"
        elif compliance_score >= 0.4:
            compliance_level = "基本合規"
        else:
            compliance_level = "需要關注"
        
        return {
            "compliance_score": compliance_score,
            "compliance_level": compliance_level,
            "safety_score": safety_score,
            "risk_level": risk_level,
            "cumulative_safety": cumulative_safety,
            "safety_trend": safety_trend,
            "round": round_number
        }
    
    async def _generate_learning_insights_v2(self, session_effectiveness: Dict, 
                                           case_usage_quality: Dict,
                                           adaptation_success: Dict,
                                           session_context: Dict) -> List[str]:
        """
        生成學習洞察 v2.0
        
        Returns:
            List[str]: 學習洞察列表
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        insights = []
        
        # 會話效果洞察
        effectiveness_score = session_effectiveness["effectiveness_score"]
        if effectiveness_score >= 0.8:
            insights.append(f"第{round_number}輪推理達到優秀效果，推理策略值得保留")
        elif effectiveness_score >= 0.65:
            insights.append(f"第{round_number}輪推理效果良好，可作為參考基準")
        else:
            insights.append(f"第{round_number}輪推理效果有待提升，需分析改進方向")
        
        # 案例使用洞察
        case_quality = case_usage_quality["overall_quality"]
        if case_quality >= 0.8:
            insights.append(f"案例使用品質優秀，{used_cases_count}個案例的選擇很合適")
        elif used_cases_count >= 5:
            insights.append("使用了較多案例，建議分析案例篩選效率")
        elif used_cases_count <= 2:
            insights.append("案例使用較少，可能需要擴大搜尋範圍")
        
        # 適配成功洞察
        adaptation_score = adaptation_success["adaptation_success_score"]
        if adaptation_score >= 0.8:
            insights.append("適配策略非常成功，適配方法值得推廣")
        elif adaptation_score < 0.5:
            insights.append("適配效果不佳，需要優化適配演算法")
        
        # 輪次特定洞察
        if round_number == 1:
            insights.append("首輪推理完成，為後續推理奠定基礎")
        elif round_number <= 3:
            insights.append(f"多輪推理進展良好，第{round_number}輪提供了更多診療選擇")
        else:
            insights.append(f"已進行{round_number}輪推理，建議評估最佳方案")
        
        # 會話級別洞察
        if round_number >= 3 and effectiveness_score > 0.8:
            insights.append("多輪螺旋推理取得良好效果，證明方法的有效性")
        
        return insights
    
    async def _recommend_knowledge_updates_v2(self, session_result: Dict, session_context: Dict) -> List[Dict[str, Any]]:
        """
        推薦知識庫更新 v2.0
        
        Returns:
            List[Dict[str, Any]]: 知識庫更新建議
        """
        round_number = session_context.get("round", 1)
        used_cases = session_context.get("used_cases", [])
        
        recommendations = []
        
        # 案例庫更新建議
        if session_result.get("confidence", 0.7) >= 0.8:
            recommendations.append({
                "type": "case_repository",
                "action": "add_successful_pattern",
                "description": f"將第{round_number}輪成功推理模式加入案例庫",
                "priority": "中等",
                "data": {
                    "session_pattern": session_result,
                    "round": round_number,
                    "effectiveness": session_result.get("confidence", 0.7)
                }
            })
        
        # 適配策略更新建議
        if len(used_cases) > 3 and session_result.get("efficacy_score", 0.7) >= 0.75:
            recommendations.append({
                "type": "adaptation_strategy",
                "action": "update_multi_case_strategy",
                "description": "更新多案例適配策略參數",
                "priority": "高",
                "data": {
                    "successful_case_count": len(used_cases),
                    "round": round_number,
                    "efficacy": session_result.get("efficacy_score", 0.7)
                }
            })
        
        # 安全性規則更新
        safety_score = session_result.get("safety_score", 0.7)
        if safety_score < 0.5:
            recommendations.append({
                "type": "safety_rules",
                "action": "strengthen_safety_checks",
                "description": f"加強第{round_number}輪類似情況的安全性檢查",
                "priority": "高",
                "data": {
                    "safety_issue": session_result,
                    "round": round_number
                }
            })
        
        # 記憶庫更新建議
        if round_number >= 3:
            recommendations.append({
                "type": "spiral_memory",
                "action": "store_multi_round_experience",
                "description": "儲存多輪推理經驗到螺旋記憶庫",
                "priority": "中等",
                "data": {
                    "session_experience": session_context,
                    "final_result": session_result
                }
            })
        
        return recommendations
    
    async def _generate_continue_recommendation_v2(self, session_effectiveness: Dict, session_context: Dict) -> Dict[str, Any]:
        """
        生成繼續推理建議 v2.0
        
        Returns:
            Dict[str, Any]: 繼續推理建議
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        effectiveness_score = session_effectiveness["effectiveness_score"]
        
        # 繼續推理的條件評估
        conditions = {
            "effectiveness_improvable": effectiveness_score < 0.85,
            "rounds_reasonable": round_number < 5,
            "cases_available": used_cases_count < 8,
            "safety_acceptable": effectiveness_score >= 0.4,
            "learning_potential": round_number <= 3 or effectiveness_score < 0.7
        }
        
        # 計算繼續推理的建議強度
        continue_confidence = sum(conditions.values()) / len(conditions)
        
        # 生成建議
        should_continue = (
            continue_confidence >= 0.6 and 
            conditions["safety_acceptable"] and 
            conditions["rounds_reasonable"]
        )
        
        return {
            "recommended": should_continue,
            "confidence": continue_confidence,
            "conditions": conditions,
            "reason": self._generate_continue_reason(should_continue, conditions, round_number, effectiveness_score),
            "round": round_number
        }
    
    async def _create_session_learning_record_v2(self, session_result: Dict, 
                                               session_context: Dict, 
                                               session_effectiveness: Dict) -> Dict[str, Any]:
        """
        創建會話學習記錄 v2.0
        
        Returns:
            Dict[str, Any]: 會話學習記錄
        """
        session_id = session_context.get("session_id", "")
        round_number = session_context.get("round", 1)
        used_cases = session_context.get("used_cases", [])
        
        return {
            "session_id": session_id,
            "total_rounds": round_number,
            "used_cases": used_cases,
            "used_cases_count": len(used_cases),
            "final_effectiveness": session_effectiveness["effectiveness_score"],
            "effectiveness_level": session_effectiveness["effectiveness_level"],
            "final_safety": session_result.get("safety_score", 0.7),
            "final_efficacy": session_result.get("efficacy_score", 0.7),
            "final_confidence": session_result.get("confidence", 0.7),
            "learning_timestamp": datetime.now().isoformat(),
            "session_pattern": {
                "round_progression": list(range(1, round_number + 1)),
                "case_usage_pattern": used_cases,
                "final_result": session_result
            },
            "learning_value": self._calculate_learning_value(session_effectiveness, session_context),
            "version": self.version
        }
    
    # 輔助方法實現
    def _calculate_round_efficiency(self, round_number: int, used_cases_count: int) -> float:
        """計算輪次效率"""
        if round_number == 0:
            return 0.5
        ideal_ratio = used_cases_count / round_number
        # 理想比例約為 1.0-1.5 案例/輪次
        if 1.0 <= ideal_ratio <= 1.5:
            return 1.0
        elif ideal_ratio < 1.0:
            return ideal_ratio
        else:
            return max(0.3, 1.5 / ideal_ratio)
    
    def _calculate_case_utilization_effectiveness(self, used_cases_count: int, round_number: int) -> float:
        """計算案例利用效果"""
        if round_number == 0:
            return 0.5
        return min(1.0, used_cases_count / (round_number * 1.2))
    
    def _assess_convergence_quality(self, session_result: Dict, session_context: Dict) -> float:
        """評估收斂品質"""
        round_number = session_context.get("round", 1)
        confidence = session_result.get("confidence", 0.7)
        
        # 輪次與信心度的理想關係
        if round_number <= 2:
            return confidence
        else:
            # 多輪推理後應該有更高信心度
            expected_confidence = min(0.85, 0.6 + round_number * 0.05)
            return min(1.0, confidence / expected_confidence)
    
    def _determine_effectiveness_level(self, effectiveness_score: float) -> str:
        """判定效果等級"""
        if effectiveness_score >= self.effectiveness_thresholds["excellent"]:
            return "優秀"
        elif effectiveness_score >= self.effectiveness_thresholds["good"]:
            return "良好"
        elif effectiveness_score >= self.effectiveness_thresholds["acceptable"]:
            return "可接受"
        else:
            return "待改善"
    
    async def _identify_improvement_areas_v2(self, session_result: Dict, session_context: Dict) -> List[str]:
        """識別改進領域 v2.0"""
        areas = []
        round_number = session_context.get("round", 1)
        
        if session_result.get("safety_score", 0.7) < 0.6:
            areas.append("安全性評估")
        
        if session_result.get("efficacy_score", 0.7) < 0.6:
            areas.append("療效預測")
        
        if session_result.get("confidence", 0.7) < 0.6:
            areas.append("適配策略")
        
        if round_number >= 4 and session_result.get("confidence", 0.7) < 0.8:
            areas.append("推理收斂效率")
        
        return areas if areas else ["系統表現良好"]
    
    def _calculate_case_efficiency(self, used_cases_count: int, round_number: int) -> float:
        """計算案例效率"""
        if round_number == 0:
            return 0.5
        efficiency = min(1.0, used_cases_count / (round_number * 2))
        return efficiency
    
    async def _analyze_case_usage_pattern_v2(self, used_cases: List[str], session_context: Dict) -> Dict[str, Any]:
        """分析案例使用模式 v2.0"""
        round_number = session_context.get("round", 1)
        
        pattern_score = 0.8  # 簡化實現
        
        return {
            "pattern_type": "progressive" if len(used_cases) == round_number else "varied",
            "pattern_score": pattern_score,
            "diversity": len(set(used_cases)) / max(len(used_cases), 1),
            "round": round_number
        }
    
    async def _assess_individual_case_quality_v2(self, used_cases: List[str], session_result: Dict) -> Dict[str, Any]:
        """評估個別案例品質 v2.0"""
        return {
            "average_quality": 0.75,  # 簡化實現
            "quality_variance": 0.1,
            "best_case": used_cases[0] if used_cases else None,
            "case_contributions": {case: 0.75 for case in used_cases}
        }
    
    def _analyze_adaptation_progression(self, session_context: Dict) -> float:
        """分析適配進展"""
        round_number = session_context.get("round", 1)
        # 簡化實現：假設適配隨輪次改善
        return min(1.0, 0.5 + round_number * 0.1)
    
    def _assess_adaptation_stability(self, session_result: Dict, round_number: int) -> float:
        """評估適配穩定性"""
        confidence = session_result.get("confidence", 0.7)
        # 多輪推理應該提高穩定性
        stability_bonus = min(round_number * 0.05, 0.2)
        return min(1.0, confidence + stability_bonus)
    
    async def _assess_cumulative_safety_v2(self, session_context: Dict) -> float:
        """評估累積安全性 v2.0"""
        round_number = session_context.get("round", 1)
        # 簡化實現：假設多輪推理提高安全性
        return min(1.0, 0.7 + round_number * 0.03)
    
    async def _analyze_safety_trend_v2(self, session_context: Dict) -> str:
        """分析安全性趨勢 v2.0"""
        round_number = session_context.get("round", 1)
        return "improving" if round_number > 1 else "stable"
    
    async def _calculate_overall_feedback_score(self, session_effectiveness: Dict, 
                                              case_usage_quality: Dict,
                                              adaptation_success: Dict, 
                                              safety_compliance: Dict) -> float:
        """計算整體反饋評分"""
        return (
            session_effectiveness["effectiveness_score"] * self.learning_weights["session_effectiveness"] +
            case_usage_quality["overall_quality"] * self.learning_weights["case_usage_quality"] +
            adaptation_success["adaptation_success_score"] * self.learning_weights["adaptation_success"] +
            safety_compliance["compliance_score"] * self.learning_weights["safety_compliance"] +
            0.8 * self.learning_weights["user_satisfaction"]  # 假設用戶滿意度
        )
    
    async def _update_knowledge_base_async_v2(self, session_learning: Dict, recommendations: List[Dict]) -> None:
        """異步更新知識庫 v2.0"""
        try:
            # 更新螺旋記憶
            if self.spiral_memory:
                await self._update_spiral_memory(session_learning)
            
            # 執行知識庫更新建議
            for rec in recommendations:
                if rec["priority"] == "高":
                    await self._execute_high_priority_update(rec)
                    
        except Exception as e:
            self.logger.error(f"知識庫異步更新失敗: {str(e)}")
    
    async def _update_spiral_memory(self, session_learning: Dict) -> None:
        """更新螺旋記憶"""
        try:
            # 簡化實現
            self.logger.info(f"更新螺旋記憶: {session_learning['session_id']}")
        except Exception as e:
            self.logger.error(f"螺旋記憶更新失敗: {str(e)}")
    
    async def _execute_high_priority_update(self, recommendation: Dict) -> None:
        """執行高優先級更新"""
        try:
            # 簡化實現
            self.logger.info(f"執行高優先級更新: {recommendation['type']} - {recommendation['action']}")
        except Exception as e:
            self.logger.error(f"高優先級更新失敗: {str(e)}")
    
    def _generate_continue_reason(self, should_continue: bool, conditions: Dict, 
                                round_number: int, effectiveness_score: float) -> str:
        """生成繼續推理原因"""
        if should_continue:
            if effectiveness_score < 0.7:
                return f"第{round_number}輪效果有待提升，建議繼續推理優化"
            elif round_number <= 2:
                return "推理輪次較少，建議探索更多診療可能"
            else:
                return "可以繼續推理以獲得更全面的診療方案"
        else:
            if not conditions["safety_acceptable"]:
                return "安全性考量，不建議繼續推理"
            elif not conditions["rounds_reasonable"]:
                return f"已進行{round_number}輪推理，建議確定方案"
            else:
                return "當前推理結果較為滿意，可考慮採用"
    
    def _calculate_learning_value(self, session_effectiveness: Dict, session_context: Dict) -> float:
        """計算學習價值"""
        effectiveness_score = session_effectiveness["effectiveness_score"]
        round_number = session_context.get("round", 1)
        
        # 高效果或多輪推理都有學習價值
        effectiveness_value = effectiveness_score
        rounds_value = min(round_number / 5, 0.3)
        
        return min(1.0, effectiveness_value + rounds_value)
    
    async def _create_fallback_feedback_v2(self, session_result: Dict, session_context: Dict) -> Dict[str, Any]:
        """創建降級反饋 v2.0"""
        round_number = session_context.get("round", 1)
        
        return {
            "session_effectiveness": 0.6,
            "effectiveness_level": "可接受",
            "learning_insights": [f"第{round_number}輪基礎反饋分析"],
            "continue_recommended": round_number < 3,
            "continue_confidence": 0.6,
            "round": round_number,
            "session_id": session_context.get("session_id", "fallback"),
            "fallback": True,
            "version": self.version
        }
    
    # 向後兼容方法（v1.0）
    async def analyze_feedback(self, session_result: Dict, **kwargs) -> Dict[str, Any]:
        """向後兼容的反饋分析"""
        session_context = {"round": 1, "session_id": "legacy", "used_cases": []}
        return await self.analyze_feedback_v2(session_result, session_context)
    
    async def update_knowledge_base(self, feedback_data: Dict, **kwargs) -> bool:
        """向後兼容的知識庫更新"""
        try:
            session_context = {"round": 1, "session_id": "legacy", "used_cases": []}
            recommendations = await self._recommend_knowledge_updates_v2(feedback_data, session_context)
            await self._update_knowledge_base_async_v2({}, recommendations)
            return True
        except Exception:
            return False

# 向後兼容的類別名稱
FeedbackAgentV2 = FeedbackAgent

__all__ = ["FeedbackAgent", "FeedbackAgentV2"]