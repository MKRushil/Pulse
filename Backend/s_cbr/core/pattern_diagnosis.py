# -*- coding: utf-8 -*-
"""
辨證-診斷雙層推理器
實現八綱、臟腑、氣血津液分類 → 病名、病機、治則推導
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
from datetime import datetime
from ..utils.logger import get_logger
from ..config import SCBRConfig

logger = get_logger("PatternDiagnosis")

@dataclass
class PatternResult:
    """辨證層結果"""
    eight_principles: List[str]  # 八綱：表裡寒熱虛實陰陽
    zangfu: List[str]  # 臟腑定位
    qi_blood_fluids: List[str]  # 氣血津液
    primary_pattern: Dict[str, Any]  # {"label": "心腎不交", "p_score": 0.88}
    secondary_patterns: List[Dict]  # [{"label": "肝腎陰虛", "p_score": 0.62}]
    explanation: str

@dataclass
class DiagnosisResult:
    """診斷層結果"""
    tcm_disease: str  # 中醫病名
    pathomechanism: str  # 病機
    treatment_principle: List[str]  # 治則治法
    formula_candidates: List[str]  # 方劑建議（已移除，根據要求）
    lifestyle_advice: List[str]  # 生活建議

class PatternDiagnosisReasoner:
    """雙層推理器"""
    
    def __init__(self, config: SCBRConfig):
        self.config = config
        self._init_knowledge_base()
        logger.info("✅ 辨證-診斷雙層推理器初始化")
    
    def _init_knowledge_base(self):
        """初始化中醫知識庫"""
        # 八綱辨證映射
        self.eight_principles_map = {
            "發熱": ["熱", "表"],
            "惡寒": ["寒", "表"],
            "自汗": ["虛", "表"],
            "盜汗": ["陰虛", "裡"],
            "疲倦": ["虛"],
            "乏力": ["氣虛"],
            "口乾": ["熱", "陰虛"],
            "便秘": ["熱", "實"],
            "腹瀉": ["寒", "虛"],
            "失眠": ["陰虛", "心"],
            "心悸": ["心", "虛"],
            "頭暈": ["虛", "陽虛"]
        }
        
        # 臟腑定位映射
        self.zangfu_map = {
            "心悸": ["心"],
            "失眠": ["心", "腎"],
            "咳嗽": ["肺"],
            "胸悶": ["肺", "心"],
            "腹脹": ["脾", "胃"],
            "便秘": ["大腸"],
            "腰痠": ["腎"],
            "頭暈": ["肝", "腎"],
            "耳鳴": ["腎", "肝"]
        }
        
        # 證型到病機映射
        self.pattern_to_pathomechanism = {
            "心腎不交": "心腎失交，水火不濟，心神失養",
            "肝腎陰虛": "肝腎陰液虧虛，虛火上擾",
            "脾腎陽虛": "脾腎陽氣不足，運化失常",
            "肝鬱氣滯": "肝氣鬱結，氣機不暢",
            "痰濕內阻": "痰濕困脾，清陽不升"
        }
        
        # 證型到治則映射
        self.pattern_to_treatment = {
            "心腎不交": ["交通心腎", "安神定志"],
            "肝腎陰虛": ["滋補肝腎", "養陰清熱"],
            "脾腎陽虛": ["溫補脾腎", "益氣健脾"],
            "肝鬱氣滯": ["疏肝解鬱", "理氣和胃"],
            "痰濕內阻": ["健脾化痰", "燥濕和胃"]
        }
    
    def infer(
        self,
        patient_ctx_fused: Dict,
        evidence_cases: List[Dict],
        round_num: int = 1
    ) -> Dict:
        """
        執行雙層推理
        
        Args:
            patient_ctx_fused: 融合後的患者上下文
            evidence_cases: 檢索到的證據案例
            round_num: 當前輪次
            
        Returns:
            包含 pattern_reasoning 和 diagnosis_reasoning 的結果
        """
        try:
            # Step 1: 辨證層推理
            pattern_result = self._pattern_reasoning(
                patient_ctx_fused, evidence_cases, round_num
            )
            
            # Step 2: 診斷層推理（基於辨證結果）
            diagnosis_result = self._diagnosis_reasoning(
                pattern_result, patient_ctx_fused, evidence_cases
            )
            
            result = {
                "pattern_reasoning": {
                    "eight_principles": pattern_result.eight_principles,
                    "zangfu": pattern_result.zangfu,
                    "qi_blood_fluids": pattern_result.qi_blood_fluids,
                    "primary_pattern": pattern_result.primary_pattern,
                    "secondary_patterns": pattern_result.secondary_patterns,
                    "explanation": pattern_result.explanation
                },
                "diagnosis_reasoning": {
                    "tcm_disease": diagnosis_result.tcm_disease,
                    "pathomechanism": diagnosis_result.pathomechanism,
                    "treatment_principle": diagnosis_result.treatment_principle,
                    "lifestyle_advice": diagnosis_result.lifestyle_advice
                }
            }
            
            logger.info(f"🔍 第{round_num}輪雙層推理完成")
            logger.info(f"   主證: {pattern_result.primary_pattern}")
            logger.info(f"   病機: {diagnosis_result.pathomechanism}")
            
            return result
            
        except Exception as e:
            logger.error(f"雙層推理失敗: {e}")
            return self._get_default_result()
    
    def _pattern_reasoning(
        self, 
        ctx: Dict, 
        cases: List[Dict], 
        round_num: int
    ) -> PatternResult:
        """
        辨證層：八綱、臟腑、氣血津液分類
        """
        # 提取症狀
        symptoms = ctx.get("symptoms", [])
        if isinstance(symptoms, str):
            symptoms = [symptoms]
        
        # 八綱分類
        eight_principles = set()
        for symptom in symptoms:
            if symptom in self.eight_principles_map:
                eight_principles.update(self.eight_principles_map[symptom])
        
        # 臟腑定位
        zangfu = set()
        for symptom in symptoms:
            if symptom in self.zangfu_map:
                zangfu.update(self.zangfu_map[symptom])
        
        # 氣血津液判斷
        qi_blood_fluids = []
        if any(s in symptoms for s in ["乏力", "疲倦", "氣短"]):
            qi_blood_fluids.append("氣虛")
        if any(s in symptoms for s in ["面色蒼白", "頭暈", "月經量少"]):
            qi_blood_fluids.append("血虛")
        if any(s in symptoms for s in ["口乾", "盜汗", "五心煩熱"]):
            qi_blood_fluids.append("陰虛")
        if any(s in symptoms for s in ["畏寒", "手足冰冷", "腰膝痠軟"]):
            qi_blood_fluids.append("陽虛")
        
        # 從案例提取證型（主證與次證）
        primary_pattern, secondary_patterns = self._extract_patterns_from_cases(
            cases, symptoms
        )
        
        # 計算證型可信度
        p_score = self._calculate_pattern_score(
            primary_pattern, symptoms, cases, round_num
        )
        
        return PatternResult(
            eight_principles=list(eight_principles),
            zangfu=list(zangfu),
            qi_blood_fluids=qi_blood_fluids,
            primary_pattern={
                "label": primary_pattern,
                "p_score": p_score
            },
            secondary_patterns=secondary_patterns,
            explanation=self._generate_pattern_explanation(
                primary_pattern, eight_principles, zangfu
            )
        )
    
    def _diagnosis_reasoning(
        self,
        pattern: PatternResult,
        ctx: Dict,
        cases: List[Dict]
    ) -> DiagnosisResult:
        """
        診斷層：病名、病機、治則推導
        """
        primary_label = pattern.primary_pattern.get("label", "")
        
        # 推導病機
        pathomechanism = self.pattern_to_pathomechanism.get(
            primary_label,
            "病機待定，需進一步辨證"
        )
        
        # 推導治則
        treatment_principle = self.pattern_to_treatment.get(
            primary_label,
            ["辨證施治", "隨症加減"]
        )
        
        # 推導中醫病名
        tcm_disease = self._infer_tcm_disease(pattern, ctx)
        
        # 生成生活建議
        lifestyle_advice = self._generate_lifestyle_advice(
            pattern, tcm_disease
        )
        
        return DiagnosisResult(
            tcm_disease=tcm_disease,
            pathomechanism=pathomechanism,
            treatment_principle=treatment_principle,
            formula_candidates=[],  # 根據要求移除方劑
            lifestyle_advice=lifestyle_advice
        )
    
    def _extract_patterns_from_cases(
        self,
        cases: List[Dict],
        symptoms: List[str]
    ) -> Tuple[str, List[Dict]]:
        """從案例中提取證型"""
        pattern_scores = {}
        
        for case in cases[:5]:  # 只看前5個案例
            # 從案例提取證型
            case_patterns = case.get("syndrome_terms", [])
            if not case_patterns and "diagnosis" in case:
                # 從診斷文本提取
                diagnosis = case["diagnosis"]
                for pattern in self.pattern_to_pathomechanism.keys():
                    if pattern in diagnosis:
                        case_patterns.append(pattern)
            
            # 計算匹配度
            case_score = case.get("_final", 0.5)
            for pattern in case_patterns:
                if pattern not in pattern_scores:
                    pattern_scores[pattern] = []
                pattern_scores[pattern].append(case_score)
        
        # 計算平均分數
        pattern_avg_scores = {
            p: sum(scores) / len(scores)
            for p, scores in pattern_scores.items()
        }
        
        # 排序選擇主證與次證
        sorted_patterns = sorted(
            pattern_avg_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        if sorted_patterns:
            primary = sorted_patterns[0][0]
            secondary = [
                {"label": p[0], "p_score": round(p[1], 2)}
                for p in sorted_patterns[1:3]
            ]
        else:
            primary = "證型待定"
            secondary = []
        
        return primary, secondary
    
    def _calculate_pattern_score(
        self,
        pattern: str,
        symptoms: List[str],
        cases: List[Dict],
        round_num: int
    ) -> float:
        """計算證型可信度分數"""
        base_score = 0.5
        
        # 案例支持度
        case_support = sum(
            1 for case in cases[:3]
            if pattern in str(case.get("syndrome_terms", []))
        ) / 3.0
        
        # 症狀覆蓋度
        symptom_coverage = len(symptoms) / 10.0  # 假設10個症狀為完整
        
        # 輪次加成
        round_bonus = min(round_num * 0.05, 0.15)
        
        score = base_score + case_support * 0.3 + symptom_coverage * 0.2 + round_bonus
        
        return min(round(score, 2), 0.99)
    
    def _infer_tcm_disease(
        self,
        pattern: PatternResult,
        ctx: Dict
    ) -> str:
        """推導中醫病名"""
        # 基於主要症狀推導
        symptoms = ctx.get("symptoms", [])
        
        if "失眠" in symptoms:
            return "不寐"
        elif "咳嗽" in symptoms:
            return "咳嗽"
        elif "頭痛" in symptoms:
            return "頭痛"
        elif "腹痛" in symptoms:
            return "腹痛"
        elif "心悸" in symptoms:
            return "心悸"
        else:
            return "雜病"
    
    def _generate_lifestyle_advice(
        self,
        pattern: PatternResult,
        tcm_disease: str
    ) -> List[str]:
        """生成生活建議"""
        advice = []
        
        # 基礎建議
        advice.append("保持規律作息，早睡早起")
        
        # 根據證型調整
        primary = pattern.primary_pattern.get("label", "")
        
        if "陰虛" in primary:
            advice.extend([
                "滋陰養陰，可食用百合、銀耳、蓮子",
                "避免熬夜，保證充足睡眠"
            ])
        elif "陽虛" in primary:
            advice.extend([
                "注意保暖，避免受寒",
                "適當運動，增強體質"
            ])
        elif "氣滯" in primary:
            advice.extend([
                "保持心情舒暢，避免情緒壓抑",
                "適當運動，促進氣血流通"
            ])
        
        return advice[:3]  # 最多3條
    
    def _generate_pattern_explanation(
        self,
        pattern: str,
        eight_principles: set,
        zangfu: set
    ) -> str:
        """生成辨證解釋"""
        explanation = f"根據症狀分析，"
        
        if eight_principles:
            explanation += f"八綱辨證為{'/'.join(eight_principles)}證，"
        
        if zangfu:
            explanation += f"病位在{'/'.join(zangfu)}，"
        
        explanation += f"綜合判斷為{pattern}。"
        
        return explanation
    
    def _get_default_result(self) -> Dict:
        """返回默認結果"""
        return {
            "pattern_reasoning": {
                "eight_principles": ["虛", "寒"],
                "zangfu": ["脾", "腎"],
                "qi_blood_fluids": ["氣虛"],
                "primary_pattern": {"label": "證型待定", "p_score": 0.5},
                "secondary_patterns": [],
                "explanation": "證候分析需要更多信息"
            },
            "diagnosis_reasoning": {
                "tcm_disease": "雜病",
                "pathomechanism": "病機待明",
                "treatment_principle": ["辨證施治"],
                "lifestyle_advice": ["規律作息", "均衡飲食", "適當運動"]
            }
        }