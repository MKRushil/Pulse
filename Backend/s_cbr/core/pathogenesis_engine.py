# -*- coding: utf-8 -*-
"""
病機推理引擎（簡化版 - 使用外部知識庫）
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from ..knowledge import knowledge_base
from ..utils.logger import get_logger

logger = get_logger("PathogenesisEngine")

@dataclass
class PathogenesisAnalysis:
    """病機分析結果"""
    etiology: List[str]
    location: List[str]
    nature: List[str]
    tendency: str
    mechanism: str
    confidence: float

class PathogenesisEngine:
    """病機推理引擎"""
    
    def __init__(self, config):
        self.config = config
        # 從知識庫載入
        self.etiology_patterns = knowledge_base.get_etiology_patterns()
        self.location_patterns = knowledge_base.get_location_patterns()
        self.nature_patterns = knowledge_base.get_nature_patterns()
        self.syndrome_patterns = knowledge_base.get_all_syndromes()
    
    def analyze(
        self,
        symptoms: List[str],
        tongue: str = "",
        pulse: str = "",
        round_num: int = 1
    ) -> PathogenesisAnalysis:
        """執行病機分析"""
        
        logger.info(f"🔬 開始病機分析 [第{round_num}輪]")
        
        # 病因分析
        etiology = self._analyze_etiology(symptoms)
        
        # 病位定位
        location = self._analyze_location(symptoms, tongue, pulse)
        
        # 病性判斷
        nature = self._analyze_nature(symptoms, tongue, pulse)
        
        # 病機推理
        mechanism, confidence = self._infer_mechanism(
            etiology, location, nature, symptoms
        )
        
        # 病勢判斷
        tendency = self._analyze_tendency(symptoms, round_num)
        
        result = PathogenesisAnalysis(
            etiology=etiology,
            location=location,
            nature=nature,
            tendency=tendency,
            mechanism=mechanism,
            confidence=confidence
        )
        
        self._log_analysis(result)
        
        return result
    
    def _analyze_etiology(self, symptoms: List[str]) -> List[str]:
        """分析病因"""
        scores = {}
        
        for category, subcategories in self.etiology_patterns.items():
            for cause, data in subcategories.items():
                indicators = data.get('indicators', [])
                match_count = sum(1 for s in symptoms if any(ind in s for ind in indicators))
                if match_count > 0:
                    scores[cause] = match_count / len(indicators)
        
        sorted_causes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [cause for cause, score in sorted_causes[:2] if score >= 0.3]
    
    def _analyze_location(self, symptoms: List[str], tongue: str, pulse: str) -> List[str]:
        """定位病位"""
        scores = {}
        
        for organ, data in self.location_patterns.items():
            indicators = data.get('primary_symptoms', [])
            symptom_match = sum(1 for s in symptoms if any(ind in s for ind in indicators))
            
            # 舌脈輔助
            tongue_match = 1 if data.get('tongue') and any(t in tongue for t in data['tongue']) else 0
            pulse_match = 1 if data.get('pulse') and any(p in pulse for p in data['pulse']) else 0
            
            total = symptom_match * 0.7 + tongue_match * 0.15 + pulse_match * 0.15
            if total > 0:
                scores[organ] = total
        
        sorted_locations = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [loc for loc, score in sorted_locations[:3] if score >= 1.0]
    
    def _analyze_nature(self, symptoms: List[str], tongue: str, pulse: str) -> List[str]:
        """判斷病性"""
        scores = {}
        
        for category, types in self.nature_patterns.items():
            for nature_type, indicators in types.items():
                all_info = symptoms + [tongue, pulse]
                match = sum(1 for info in all_info if any(ind in str(info) for ind in indicators))
                if match > 0:
                    scores[nature_type] = match / len(indicators)
        
        sorted_natures = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [nat for nat, score in sorted_natures[:3] if score >= 0.3]
    
    def _infer_mechanism(
        self,
        etiology: List[str],
        location: List[str],
        nature: List[str],
        symptoms: List[str]
    ) -> Tuple[str, float]:
        """推理病機"""
        
        best_match = None
        best_score = 0.0
        
        for syndrome_name, syndrome_data in self.syndrome_patterns.items():
            # 病位匹配
            required_zangfu = syndrome_data.get('zangfu', [])
            if not required_zangfu:
                continue
                
            loc_match = len(set(location) & set(required_zangfu)) / len(required_zangfu)
            
            # 病性匹配
            required_nature = syndrome_data.get('nature', [])
            nat_match = len(set(nature) & set(required_nature)) / len(required_nature) if required_nature else 0
            
            # 症狀匹配
            key_symptoms = syndrome_data.get('key_symptoms', [])
            sym_match = len(set(symptoms) & set(key_symptoms)) / len(key_symptoms) if key_symptoms else 0
            
            score = loc_match * 0.4 + nat_match * 0.3 + sym_match * 0.3
            
            if score > best_score:
                best_score = score
                best_match = syndrome_name
        
        if best_match and best_score >= 0.5:
            mechanism = self.syndrome_patterns[best_match].get('pathogenesis', '')
            return mechanism, best_score
        
        return self._generate_generic_mechanism(location, nature), 0.4
    
    def _generate_generic_mechanism(self, location: List[str], nature: List[str]) -> str:
        """生成通用病機"""
        if not location or not nature:
            return "病機尚不明確，需進一步辨證"
        return f"{('、'.join(location))}功能失調，表現為{('、'.join(nature))}之證"
    
    def _analyze_tendency(self, symptoms: List[str], round_num: int) -> str:
        """判斷病勢"""
        acute_keywords = ["劇痛", "高熱", "昏迷", "抽搐", "大汗"]
        chronic_keywords = ["反覆", "時作", "隱痛", "緩解"]
        
        acute = sum(1 for s in symptoms if any(k in s for k in acute_keywords))
        chronic = sum(1 for s in symptoms if any(k in s for k in chronic_keywords))
        
        if acute > 0:
            return "病勢急迫"
        elif round_num >= 3 and chronic > 0:
            return "病勢緩慢，病程較長"
        return "病勢平穩"
    
    def _log_analysis(self, result: PathogenesisAnalysis):
        """記錄分析結果"""
        logger.info(f"📋 病機分析結果:")
        logger.info(f"   病因: {', '.join(result.etiology) if result.etiology else '待定'}")
        logger.info(f"   病位: {', '.join(result.location) if result.location else '待定'}")
        logger.info(f"   病性: {', '.join(result.nature) if result.nature else '待定'}")
        logger.info(f"   病機: {result.mechanism}")
        logger.info(f"   置信度: {result.confidence:.1%}")