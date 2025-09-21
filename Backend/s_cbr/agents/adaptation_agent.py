"""
中醫適配智能體 v2.0

負責將相似案例適配到當前患者的具體情況
支援會話上下文與多輪推理適配策略

版本：v2.0 - 螺旋互動版
更新：支援會話上下文處理與輪次感知適配
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..knowledge.pulse_repository import PulseRepository
    from ..utils.api_manager import SCBRAPIManager
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    PulseRepository = None
    SCBRAPIManager = None

class AdaptationAgent:
    """
    中醫適配智能體 v2.0
    
    v2.0 特色：
    - 會話上下文感知適配
    - 輪次權重動態調整
    - 多輪推理策略優化
    - 脈診知識深度整合
    """
    
    def __init__(self):
        """初始化適配智能體 v2.0"""
        self.logger = SpiralLogger.get_logger("AdaptationAgent") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("AdaptationAgent")
        self.version = "2.0"
        
        # 初始化脈診知識庫
        self.pulse_repository = PulseRepository() if PulseRepository else None
        self.api_manager = SCBRAPIManager() if SCBRAPIManager else None
        
        self.logger.info(f"中醫適配智能體 v{self.version} 初始化完成")
    
    async def create_adaptation_strategy_v2(self, 
                                          base_case: Dict[str, Any],
                                          patient_query: Dict[str, Any],
                                          session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        創建適配策略 v2.0 - 支援會話上下文
        
        Args:
            base_case: 基準案例
            patient_query: 患者查詢信息
            session_context: 會話上下文（session_id, round, used_cases等）
            
        Returns:
            Dict[str, Any]: 適配策略結果
        """
        try:
            session_id = session_context.get("session_id", "")
            round_number = session_context.get("round", 1)
            used_cases_count = len(session_context.get("used_cases", []))
            
            self.logger.info(f"開始適配策略 v2.0 - Session: {session_id}, Round: {round_number}")
            
            # 1. 分析案例與患者差異（v2.0 增強）
            differences = await self._analyze_case_patient_differences_v2(
                base_case, patient_query, session_context
            )
            
            # 2. 制定脈診整合策略（v2.0 增強）
            pulse_strategy = await self._develop_pulse_integration_strategy_v2(
                base_case, patient_query, session_context
            )
            
            # 3. 確定適配優先級（基於輪次）
            priorities = await self._determine_adaptation_priorities_v2(
                differences, round_number, used_cases_count
            )
            
            # 4. 生成適配方案（輪次感知）
            adaptation_pathway = await self._generate_adaptation_pathway_v2(
                base_case, differences, pulse_strategy, priorities, session_context
            )
            
            # 5. 評估適配風險（會話級別）
            risk_assessment = await self._assess_adaptation_risks_v2(
                adaptation_pathway, session_context
            )
            
            # 6. 計算策略信心度（基於會話歷史）
            confidence = await self._calculate_strategy_confidence_v2(
                differences, pulse_strategy, session_context
            )
            
            # 7. 估算成功率（多輪推理修正）
            success_rate = await self._estimate_success_rate_v2(
                adaptation_pathway, risk_assessment, session_context
            )
            
            # 構建最終適配結果
            adaptation_result = {
                "diagnosis": adaptation_pathway.get("adapted_diagnosis", ""),
                "treatment_plan": adaptation_pathway.get("adapted_treatment", ""),
                "modifications": adaptation_pathway.get("modifications", []),
                "pulse_integration": pulse_strategy,
                "risk_assessment": risk_assessment,
                "confidence": confidence,
                "success_rate": success_rate,
                "adaptation_rationale": adaptation_pathway.get("rationale", ""),
                "round": round_number,
                "session_id": session_id,
                "version": self.version
            }
            
            self.logger.info(f"適配策略 v2.0 完成 - 信心度: {confidence:.3f}, 成功率: {success_rate:.3f}")
            
            return adaptation_result
            
        except Exception as e:
            self.logger.error(f"適配策略 v2.0 失敗: {str(e)}")
            return await self._create_fallback_strategy_v2(base_case, patient_query, session_context)
    
    async def _analyze_case_patient_differences_v2(self, 
                                                 base_case: Dict, 
                                                 patient_query: Dict,
                                                 session_context: Dict) -> Dict[str, Any]:
        """
        分析案例與患者差異 v2.0 - 會話感知分析
        
        Returns:
            Dict[str, Any]: 差異分析結果
        """
        round_number = session_context.get("round", 1)
        
        # 基本差異分析
        demographic_diff = self._analyze_demographic_diff(base_case, patient_query)
        symptom_diff = self._analyze_symptom_diff(base_case, patient_query)
        constitution_diff = self._analyze_constitution_diff(base_case, patient_query)
        pulse_diff = await self._analyze_pulse_diff_v2(base_case, patient_query, session_context)
        severity_diff = self._analyze_severity_diff(base_case, patient_query)
        
        # v2.0: 計算整體相似度（考慮輪次權重）
        overall_similarity = await self._calculate_overall_similarity_v2(
            demographic_diff, symptom_diff, constitution_diff, pulse_diff, severity_diff, round_number
        )
        
        # v2.0: 識別關鍵差異點（基於輪次重點）
        key_differences = await self._identify_key_differences_v2(
            demographic_diff, symptom_diff, constitution_diff, pulse_diff, severity_diff, round_number
        )
        
        return {
            "demographic_diff": demographic_diff,
            "symptom_diff": symptom_diff,
            "constitution_diff": constitution_diff,
            "pulse_diff": pulse_diff,
            "severity_diff": severity_diff,
            "overall_similarity": overall_similarity,
            "key_differences": key_differences,
            "round": round_number
        }
    
    async def _develop_pulse_integration_strategy_v2(self,
                                                   base_case: Dict,
                                                   patient_query: Dict,
                                                   session_context: Dict) -> Dict[str, Any]:
        """
        制定脈診整合策略 v2.0 - 增強脈診知識運用
        
        Returns:
            Dict[str, Any]: 脈診整合策略
        """
        round_number = session_context.get("round", 1)
        patient_ctx = patient_query.get("patient_ctx", {})
        pulse_text = patient_ctx.get("pulse_text", "")
        
        # 脈診支撐強度評估
        pulse_support_strength = await self._assess_pulse_support_strength(pulse_text, base_case)
        
        # v2.0: 脈診整合策略（考慮輪次）
        pulse_integration = await self._formulate_pulse_integration_v2(
            pulse_text, base_case, pulse_support_strength, round_number
        )
        
        # v2.0: 脈診知識利用率
        knowledge_utilization = await self._calculate_knowledge_utilization(pulse_text, round_number)
        
        return {
            "pulse_text": pulse_text,
            "pulse_support_strength": pulse_support_strength,
            "integration_strategy": pulse_integration,
            "knowledge_utilization": knowledge_utilization,
            "integration_quality": min(pulse_support_strength * knowledge_utilization, 1.0),
            "round": round_number
        }
    
    async def _determine_adaptation_priorities_v2(self,
                                                differences: Dict,
                                                round_number: int,
                                                used_cases_count: int) -> List[str]:
        """
        確定適配優先級 v2.0 - 基於輪次的策略調整
        
        Returns:
            List[str]: 優先級排序的適配重點
        """
        base_priorities = []
        
        # 第1輪：專注於主要症狀匹配
        if round_number == 1:
            base_priorities = ["symptom_diff", "severity_diff", "constitution_diff"]
        
        # 第2輪：加強體質與脈診匹配
        elif round_number == 2:
            base_priorities = ["constitution_diff", "pulse_diff", "demographic_diff"]
        
        # 第3輪及以後：精細化調整
        else:
            base_priorities = ["pulse_diff", "demographic_diff", "symptom_diff"]
        
        # 根據差異程度動態調整優先級
        diff_scores = {}
        for key in base_priorities:
            if key in differences:
                diff_scores[key] = differences[key].get("difference_score", 0.5)
        
        # 按差異分數排序（差異越大，優先級越高）
        sorted_priorities = sorted(base_priorities, key=lambda x: diff_scores.get(x, 0.5), reverse=True)
        
        self.logger.info(f"Round {round_number} 適配優先級: {sorted_priorities}")
        
        return sorted_priorities
    
    async def _generate_adaptation_pathway_v2(self,
                                            base_case: Dict,
                                            differences: Dict,
                                            pulse_strategy: Dict,
                                            priorities: List[str],
                                            session_context: Dict) -> Dict[str, Any]:
        """
        生成適配路徑 v2.0 - 輪次感知的適配策略
        
        Returns:
            Dict[str, Any]: 適配路徑與策略
        """
        round_number = session_context.get("round", 1)
        session_id = session_context.get("session_id", "")
        
        # 基礎診斷與治療
        base_diagnosis = base_case.get("diagnosis", "")
        base_treatment = base_case.get("treatment", "")
        
        # 根據輪次調整適配強度
        adaptation_weight = self._calculate_round_weight(round_number)
        
        # 生成適配後的診斷
        adapted_diagnosis = await self._adapt_diagnosis_v2(
            base_diagnosis, differences, pulse_strategy, priorities, adaptation_weight
        )
        
        # 生成適配後的治療方案
        adapted_treatment = await self._adapt_treatment_v2(
            base_treatment, differences, pulse_strategy, priorities, adaptation_weight
        )
        
        # 記錄適配修改
        modifications = await self._track_modifications_v2(
            base_case, adapted_diagnosis, adapted_treatment, differences, round_number
        )
        
        # 生成適配理由
        rationale = await self._generate_adaptation_rationale_v2(
            base_case, differences, priorities, round_number
        )
        
        return {
            "adapted_diagnosis": adapted_diagnosis,
            "adapted_treatment": adapted_treatment,
            "modifications": modifications,
            "rationale": rationale,
            "adaptation_weight": adaptation_weight,
            "round": round_number,
            "session_id": session_id
        }
    
    def _calculate_round_weight(self, round_number: int) -> float:
        """
        計算輪次權重
        
        Args:
            round_number: 當前輪次
            
        Returns:
            float: 適配權重 (0.0-1.0)
        """
        # 第1輪：高權重適配 (0.8)
        # 第2輪：中等權重適配 (0.6) 
        # 第3輪及以後：輕度適配 (0.4-0.2)
        
        if round_number == 1:
            return 0.8
        elif round_number == 2:
            return 0.6
        elif round_number == 3:
            return 0.4
        else:
            return max(0.2, 0.4 - (round_number - 3) * 0.05)
    
    async def _assess_adaptation_risks_v2(self,
                                        adaptation_pathway: Dict,
                                        session_context: Dict) -> Dict[str, Any]:
        """
        評估適配風險 v2.0 - 會話級別風險評估
        
        Returns:
            Dict[str, Any]: 風險評估結果
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        # 基礎風險因素
        adaptation_weight = adaptation_pathway.get("adaptation_weight", 0.5)
        modifications_count = len(adaptation_pathway.get("modifications", []))
        
        # v2.0: 會話級別風險因素
        round_risk = min(round_number * 0.1, 0.3)  # 輪次風險
        case_diversity_risk = min(used_cases_count * 0.05, 0.2)  # 案例多樣性風險
        
        # 計算總體風險評分
        total_risk = min(
            adaptation_weight * 0.3 +
            modifications_count * 0.1 +
            round_risk +
            case_diversity_risk,
            1.0
        )
        
        # 風險等級判定
        if total_risk < 0.3:
            risk_level = "低"
        elif total_risk < 0.6:
            risk_level = "中"
        else:
            risk_level = "高"
        
        return {
            "total_risk_score": total_risk,
            "risk_level": risk_level,
            "risk_factors": {
                "adaptation_weight": adaptation_weight * 0.3,
                "modifications_count": modifications_count * 0.1,
                "round_risk": round_risk,
                "case_diversity_risk": case_diversity_risk
            },
            "recommendations": self._generate_risk_recommendations(risk_level, round_number)
        }
    
    async def _calculate_strategy_confidence_v2(self,
                                              differences: Dict,
                                              pulse_strategy: Dict,
                                              session_context: Dict) -> float:
        """
        計算策略信心度 v2.0 - 基於會話歷史
        
        Returns:
            float: 信心度評分 (0.0-1.0)
        """
        round_number = session_context.get("round", 1)
        used_cases_count = len(session_context.get("used_cases", []))
        
        # 基礎信心度因素
        similarity_confidence = differences.get("overall_similarity", 0.5)
        pulse_confidence = pulse_strategy.get("integration_quality", 0.5)
        
        # v2.0: 會話歷史調整
        round_adjustment = max(0.7, 1.0 - (round_number - 1) * 0.1)
        case_diversity_bonus = min(used_cases_count * 0.05, 0.2)
        
        # 計算最終信心度
        final_confidence = min(
            (similarity_confidence * 0.4 + pulse_confidence * 0.4) * round_adjustment + case_diversity_bonus,
            1.0
        )
        
        return max(final_confidence, 0.3)  # 最低信心度保障
    
    async def _estimate_success_rate_v2(self,
                                      adaptation_pathway: Dict,
                                      risk_assessment: Dict,
                                      session_context: Dict) -> float:
        """
        估算成功率 v2.0 - 多輪推理修正
        
        Returns:
            float: 成功率估算 (0.0-1.0)
        """
        round_number = session_context.get("round", 1)
        
        # 基礎成功率
        base_success_rate = 0.8
        
        # 風險調整
        risk_penalty = risk_assessment.get("total_risk_score", 0.5) * 0.3
        
        # 輪次調整（後續輪次成功率略降）
        round_penalty = min((round_number - 1) * 0.05, 0.2)
        
        # 適配質量加成
        adaptation_quality = len(adaptation_pathway.get("modifications", [])) * 0.02
        
        # 計算最終成功率
        final_success_rate = max(
            base_success_rate - risk_penalty - round_penalty + adaptation_quality,
            0.4  # 最低成功率保障
        )
        
        return min(final_success_rate, 0.95)  # 最高成功率限制
    
    # 輔助方法實現 (簡化版)
    def _analyze_demographic_diff(self, base_case: Dict, patient_query: Dict) -> Dict:
        """分析人口統計學差異"""
        return {
            "difference_score": 0.3,
            "key_factors": ["年齡", "性別"],
            "impact_level": "中等"
        }
    
    def _analyze_symptom_diff(self, base_case: Dict, patient_query: Dict) -> Dict:
        """分析症狀差異"""
        return {
            "difference_score": 0.4,
            "key_factors": ["主要症狀", "次要症狀"],
            "impact_level": "較高"
        }
    
    def _analyze_constitution_diff(self, base_case: Dict, patient_query: Dict) -> Dict:
        """分析體質差異"""
        return {
            "difference_score": 0.2,
            "key_factors": ["體質類型"],
            "impact_level": "較低"
        }
    
    async def _analyze_pulse_diff_v2(self, base_case: Dict, patient_query: Dict, session_context: Dict) -> Dict:
        """分析脈診差異 v2.0"""
        return {
            "difference_score": 0.3,
            "key_factors": ["脈象特徵"],
            "impact_level": "中等",
            "round": session_context.get("round", 1)
        }
    
    def _analyze_severity_diff(self, base_case: Dict, patient_query: Dict) -> Dict:
        """分析嚴重程度差異"""
        return {
            "difference_score": 0.35,
            "key_factors": ["病情嚴重程度"],
            "impact_level": "中等"
        }
    
    async def _calculate_overall_similarity_v2(self, *args, round_number: int) -> float:
        """計算整體相似度 v2.0"""
        # 簡化實現
        base_similarity = 0.7
        round_adjustment = max(0.9, 1.0 - (round_number - 1) * 0.1)
        return base_similarity * round_adjustment
    
    async def _identify_key_differences_v2(self, *args, round_number: int) -> List[str]:
        """識別關鍵差異 v2.0"""
        return [f"關鍵差異點{i}" for i in range(1, round_number + 1)]
    
    async def _assess_pulse_support_strength(self, pulse_text: str, base_case: Dict) -> float:
        """評估脈診支撐強度"""
        return 0.75 if pulse_text else 0.5
    
    async def _formulate_pulse_integration_v2(self, pulse_text: str, base_case: Dict, 
                                            strength: float, round_number: int) -> Dict:
        """制定脈診整合策略 v2.0"""
        return {
            "integration_approach": f"第{round_number}輪脈診整合",
            "key_insights": ["脈診要點1", "脈診要點2"],
            "confidence": strength
        }
    
    async def _calculate_knowledge_utilization(self, pulse_text: str, round_number: int) -> float:
        """計算知識利用率"""
        base_utilization = 0.8 if pulse_text else 0.6
        return base_utilization * (1.0 - (round_number - 1) * 0.1)
    
    async def _adapt_diagnosis_v2(self, base_diagnosis: str, differences: Dict, 
                                pulse_strategy: Dict, priorities: List[str], weight: float) -> str:
        """適配診斷 v2.0"""
        if not base_diagnosis:
            return "基於多輪推理的中醫診斷"
        
        # 簡化實現：基於權重調整診斷
        adaptation_level = "重度" if weight > 0.7 else "中度" if weight > 0.4 else "輕度"
        return f"{base_diagnosis} ({adaptation_level}適配)"
    
    async def _adapt_treatment_v2(self, base_treatment: str, differences: Dict,
                                pulse_strategy: Dict, priorities: List[str], weight: float) -> str:
        """適配治療方案 v2.0"""
        if not base_treatment:
            return "基於螺旋推理的個性化治療方案"
            
        adaptation_level = "重度" if weight > 0.7 else "中度" if weight > 0.4 else "輕度"
        return f"{base_treatment} ({adaptation_level}適配)"
    
    async def _track_modifications_v2(self, base_case: Dict, adapted_diagnosis: str,
                                    adapted_treatment: str, differences: Dict, round_number: int) -> List[str]:
        """追蹤修改記錄 v2.0"""
        return [
            f"第{round_number}輪診斷調整",
            f"第{round_number}輪治療優化",
            "脈診因素整合"
        ]
    
    async def _generate_adaptation_rationale_v2(self, base_case: Dict, differences: Dict,
                                              priorities: List[str], round_number: int) -> str:
        """生成適配理由 v2.0"""
        return f"基於第{round_number}輪螺旋推理，針對關鍵差異點{priorities[:2]}進行個性化適配"
    
    def _generate_risk_recommendations(self, risk_level: str, round_number: int) -> List[str]:
        """生成風險建議"""
        if risk_level == "高":
            return [f"第{round_number}輪推理風險較高，建議諮詢專業醫師", "密切監控治療反應"]
        elif risk_level == "中":
            return [f"第{round_number}輪適配風險適中，建議觀察療效"]
        else:
            return [f"第{round_number}輪推理風險較低，可以安全使用"]
    
    async def _create_fallback_strategy_v2(self, base_case: Dict, patient_query: Dict, 
                                         session_context: Dict) -> Dict[str, Any]:
        """創建降級策略 v2.0"""
        round_number = session_context.get("round", 1)
        
        return {
            "diagnosis": base_case.get("diagnosis", f"第{round_number}輪診斷分析"),
            "treatment_plan": base_case.get("treatment", f"第{round_number}輪治療建議"),
            "modifications": [f"第{round_number}輪基礎適配"],
            "confidence": max(0.5, 0.8 - round_number * 0.1),
            "success_rate": max(0.6, 0.9 - round_number * 0.1),
            "round": round_number,
            "fallback": True,
            "version": self.version
        }
    
    # 向後兼容方法（v1.0）
    async def create_adaptation_strategy_v1(self, base_case: Dict, patient_query: Dict, **kwargs) -> Dict[str, Any]:
        """向後兼容的 v1.0 方法"""
        session_context = {"round": 1, "session_id": "legacy", "used_cases": []}
        return await self.create_adaptation_strategy_v2(base_case, patient_query, session_context)

# 向後兼容的類別名稱
AdaptationAgentV2 = AdaptationAgent

__all__ = ["AdaptationAgent", "AdaptationAgentV2"]