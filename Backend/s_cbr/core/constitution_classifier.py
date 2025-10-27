# -*- coding: utf-8 -*-
"""
體質分類器（簡化版 - 使用外部知識庫）
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from ..knowledge import knowledge_base
from ..utils.logger import get_logger

logger = get_logger("ConstitutionClassifier")

@dataclass
class ConstitutionResult:
    """體質判定結果"""
    primary_type: str
    secondary_type: str
    scores: Dict[str, float]
    characteristics: List[str]
    suggestions: List[str]

class ConstitutionClassifier:
    """體質分類器"""
    
    def __init__(self, config):
        self.config = config
        self.constitutions = knowledge_base.get_all_constitutions()
    
    def classify(
        self,
        symptoms: List[str],
        patient_info: Dict[str, Any]
    ) -> ConstitutionResult:
        """判定體質類型"""
        
        logger.info("🧬 開始體質分析")
        
        scores = {}
        for const_type, const_data in self.constitutions.items():
            score = self._calculate_score(const_type, const_data, symptoms)
            scores[const_type] = score
        
        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = sorted_types[0][0]
        secondary = sorted_types[1][0] if len(sorted_types) > 1 and sorted_types[1][1] >= 0.3 else None
        
        characteristics = self._extract_characteristics(primary, symptoms)
        suggestions = self._get_suggestions(primary)
        
        result = ConstitutionResult(
            primary_type=primary,
            secondary_type=secondary,
            scores=scores,
            characteristics=characteristics,
            suggestions=suggestions
        )
        
        self._log_result(result)
        
        return result
    
    def _calculate_score(
        self,
        const_type: str,
        const_data: Dict,
        symptoms: List[str]
    ) -> float:
        """計算體質評分"""
        
        characteristics = const_data.get('characteristics', {})
        total_score = 0.0
        max_score = 0.0
        
        for category, keywords in characteristics.items():
            if isinstance(keywords, list):
                match_count = sum(1 for s in symptoms if any(k in s for k in keywords))
                category_score = match_count / len(keywords) if keywords else 0
                total_score += category_score
                max_score += 1.0
        
        return total_score / max_score if max_score > 0 else 0.0
    
    def _extract_characteristics(self, const_type: str, symptoms: List[str]) -> List[str]:
        """提取體質特徵"""
        const_data = self.constitutions.get(const_type, {})
        characteristics = const_data.get('characteristics', {})
        
        matched = []
        for category, keywords in characteristics.items():
            if isinstance(keywords, list):
                for s in symptoms:
                    if any(k in s for k in keywords):
                        matched.append(s)
                        if len(matched) >= 5:
                            return matched[:5]
        
        return matched[:5]
    
    def _get_suggestions(self, const_type: str) -> List[str]:
        """獲取調養建議"""
        const_data = self.constitutions.get(const_type, {})
        advice = const_data.get('health_advice', {})
        
        suggestions = []
        
        # 飲食建議
        diet = advice.get('飲食', [])
        if isinstance(diet, dict):
            should_eat = diet.get('宜', [])
            if should_eat:
                suggestions.append(f"飲食調養：宜食 {', '.join(should_eat[:5])}")
        
        # 運動建議
        exercise = advice.get('運動', [])
        if exercise:
            suggestions.append(f"運動方式：{', '.join(exercise[:3]) if isinstance(exercise, list) else exercise}")
        
        # 作息建議
        lifestyle = advice.get('作息', [])
        if lifestyle:
            suggestions.append(f"作息調理：{', '.join(lifestyle[:3]) if isinstance(lifestyle, list) else lifestyle}")
        
        return suggestions
    
    def _log_result(self, result: ConstitutionResult):
        """記錄分類結果"""
        logger.info(f"🧬 體質判定結果:")
        logger.info(f"   主要體質: {result.primary_type} ({result.scores[result.primary_type]:.1%})")
        if result.secondary_type:
            logger.info(f"   次要體質: {result.secondary_type} ({result.scores[result.secondary_type]:.1%})")