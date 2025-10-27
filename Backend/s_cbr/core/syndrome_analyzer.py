# -*- coding: utf-8 -*-
"""
證候分析器（簡化版）
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .pathogenesis_engine import PathogenesisEngine, PathogenesisAnalysis
from .constitution_classifier import ConstitutionClassifier, ConstitutionResult
from ..knowledge import knowledge_base
from ..utils.logger import get_logger

logger = get_logger("SyndromeAnalyzer")

@dataclass
class SyndromeDiagnosis:
    """證候診斷結果"""
    primary_syndrome: str
    secondary_syndromes: List[str]
    pathogenesis: PathogenesisAnalysis
    constitution: ConstitutionResult
    treatment_principle: str
    prognosis: str
    confidence: float

class SyndromeAnalyzer:
    """證候分析器"""
    
    def __init__(self, config):
        self.config = config
        self.pathogenesis_engine = PathogenesisEngine(config)
        self.constitution_classifier = ConstitutionClassifier(config)
        self.syndromes = knowledge_base.get_all_syndromes()
    
    def analyze(
        self,
        symptoms: List[str],
        tongue: str = "",
        pulse: str = "",
        patient_info: Dict[str, Any] = None,
        round_num: int = 1
    ) -> SyndromeDiagnosis:
        """執行完整辨證分析"""
        
        logger.info(f"🔬 開始辨證分析 [第{round_num}輪]")
        
        # 病機分析
        pathogenesis = self.pathogenesis_engine.analyze(symptoms, tongue, pulse, round_num)
        
        # 體質判定
        constitution = self.constitution_classifier.classify(symptoms, patient_info or {})
        
        # 證型推理
        primary, secondary, confidence = self._infer_syndrome(pathogenesis, symptoms)
        
        # 治則
        treatment = self._get_treatment_principle(primary)
        
        # 預後
        prognosis = self._evaluate_prognosis(pathogenesis, constitution, round_num)
        
        result = SyndromeDiagnosis(
            primary_syndrome=primary,
            secondary_syndromes=secondary,
            pathogenesis=pathogenesis,
            constitution=constitution,
            treatment_principle=treatment,
            prognosis=prognosis,
            confidence=confidence
        )
        
        self._log_diagnosis(result)
        
        return result
    
    def _infer_syndrome(
        self,
        pathogenesis: PathogenesisAnalysis,
        symptoms: List[str]
    ) -> tuple[str, List[str], float]:
        """推理證型"""
        
        scores = {}
        
        for syndrome_name, syndrome_data in self.syndromes.items():
            # 病位匹配
            required_zangfu = syndrome_data.get('zangfu', [])
            loc_match = len(set(pathogenesis.location) & set(required_zangfu)) / len(required_zangfu) if required_zangfu else 0
            
            # 病性匹配
            required_nature = syndrome_data.get('nature', [])
            nat_match = len(set(pathogenesis.nature) & set(required_nature)) / len(required_nature) if required_nature else 0
            
            # 症狀匹配
            key_symptoms = syndrome_data.get('key_symptoms', [])
            min_match = syndrome_data.get('min_symptom_match', 3)
            symptom_match_count = len(set(symptoms) & set(key_symptoms))
            
            if symptom_match_count < min_match:
                continue
            
            sym_match = symptom_match_count / len(key_symptoms)
            
            score = loc_match * 0.4 + nat_match * 0.3 + sym_match * 0.3
            
            if score > 0:
                scores[syndrome_name] = score
        
        if not scores:
            return "證型待定", [], 0.0
        
        sorted_syndromes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = sorted_syndromes[0][0]
        primary_score = sorted_syndromes[0][1]
        
        secondary = [syn for syn, score in sorted_syndromes[1:3] if score >= 0.4]
        
        return primary, secondary, primary_score
    
    def _get_treatment_principle(self, syndrome: str) -> str:
        """獲取治則"""
        syndrome_data = self.syndromes.get(syndrome, {})
        return syndrome_data.get('treatment_principle', '辨證論治')
    
    def _evaluate_prognosis(
        self,
        pathogenesis: PathogenesisAnalysis,
        constitution: ConstitutionResult,
        round_num: int
    ) -> str:
        """評估預後"""
        if pathogenesis.confidence >= 0.7 and round_num >= 2:
            if constitution.primary_type == "平和質":
                return "預後良好，調理後可恢復"
            elif constitution.primary_type in ["氣虛質", "陽虛質", "陰虛質"]:
                return "需持續調理，預後尚可"
            return "需長期調理，注意生活起居"
        return "需進一步觀察，補充更多症狀資訊"
    
    def _log_diagnosis(self, result: SyndromeDiagnosis):
        """記錄診斷結果"""
        logger.info("=" * 60)
        logger.info("📋 辨證診斷結果")
        logger.info("=" * 60)
        logger.info(f"【主證】{result.primary_syndrome} (置信度: {result.confidence:.1%})")
        if result.secondary_syndromes:
            logger.info(f"【兼證】{', '.join(result.secondary_syndromes)}")
        logger.info(f"【病機】{result.pathogenesis.mechanism}")
        logger.info(f"【體質】{result.constitution.primary_type}")
        logger.info(f"【治則】{result.treatment_principle}")
        logger.info("=" * 60)