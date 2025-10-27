# -*- coding: utf-8 -*-
"""
Backend/s_cbr/core/query_expander.py
查詢擴充器 - 同義詞映射、否定詞綁定、查詢重構
"""

from typing import Dict, List, Set, Tuple
import re
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger("QueryExpander")

@dataclass
class ExpansionConfig:
    """查詢擴充配置"""
    # 重複權重
    original_weight: int = 3  # 原詞重複 3 次
    synonym_weight: int = 1   # 同義詞重複 1 次
    mapping_weight: int = 1   # 映射詞重複 1 次
    
    # 啟用功能開關
    enable_synonym: bool = True
    enable_negation_binding: bool = True
    enable_tcm_mapping: bool = True

class QueryExpander:
    """查詢擴充器"""
    
    def __init__(self, config: ExpansionConfig = None):
        self.config = config or ExpansionConfig()
        
        # ==================== 同義詞映射表 ====================
        self.synonym_map = {
            # 睡眠相關
            "易醒": ["睡眠淺", "驚醒", "多醒"],
            "睡眠淺": ["易醒", "睡不安穩"],
            "入睡難": ["入睡困難", "難以入眠"],
            
            # 心悸相關
            "心悶": ["胸悶", "心胸悶"],
            "心慌": ["心悸", "心跳快"],
            "心煩": ["煩躁", "心中煩熱"],
            
            # 口乾相關
            "口乾": ["口渴", "咽乾"],
            "欲溫飲": ["口乾喜飲溫水", "喜溫飲"],
            "欲冷飲": ["口乾喜冷飲", "喜冷飲"],
            
            # 疼痛相關
            "頭痛": ["頭疼", "腦痛"],
            "腹痛": ["肚子痛", "腹部疼痛"],
            "胸痛": ["胸口痛", "前胸痛"],
            
            # 疲勞相關
            "疲倦": ["乏力", "倦怠", "疲勞"],
            "乏力": ["無力", "神疲", "氣短乏力"],
            
            # 消化相關
            "食慾不振": ["胃口差", "不想吃", "納差"],
            "腹脹": ["肚子脹", "胃脹", "脹滿"],
            "便秘": ["大便乾", "大便難", "排便困難"],
            "腹瀉": ["拉肚子", "便溏", "大便稀"],
            
            # 情志相關
            "焦慮": ["擔心", "緊張", "心神不寧"],
            "抑鬱": ["情緒低落", "心情低落", "不開心"],
            "易怒": ["容易生氣", "煩躁易怒"],
        }
        
        # ==================== 中醫映射表 ====================
        self.tcm_mapping = {
            # 舌象映射
            "舌尖紅": ["心火", "陰虛火旺"],
            "舌質淡": ["氣血虛", "陽虛"],
            "舌質紅": ["熱證", "陰虛"],
            "舌紫暗": ["血瘀", "氣滯血瘀"],
            "舌苔厚膩": ["痰濕", "濕熱"],
            
            # 脈象映射
            "細脈": ["血虛", "陰虛"],
            "遲脈": ["寒證", "陽虛"],
            "數脈": ["熱證", "陰虛火旺"],
            "弦脈": ["肝鬱", "肝陽上亢"],
            "滑脈": ["痰濕", "食積"],
            
            # 症狀映射
            "手足冰冷": ["陽虛", "寒證"],
            "五心煩熱": ["陰虛", "陰虛火旺"],
            "盜汗": ["陰虛", "營衛不和"],
            "自汗": ["氣虛", "陽虛"],
            "潮熱": ["陰虛", "濕熱"],
        }
        
        # ==================== 否定詞列表 ====================
        self.negation_words = {
            "無", "沒有", "不", "未", "非", "否",
            "沒", "無明顯", "不太", "不怎麼"
        }
        
        # ==================== 程度詞列表 ====================
        self.degree_words = {
            "很", "非常", "特別", "極", "稍", "略",
            "有點", "比較", "較", "些許", "輕微"
        }
        
        logger.info("✅ 查詢擴充器初始化")
        logger.info(f"   同義詞映射: {len(self.synonym_map)} 組")
        logger.info(f"   中醫映射: {len(self.tcm_mapping)} 組")
    
    # ==================== 核心擴充方法 ====================
    def expand_query(
        self,
        query: str,
        symptoms: List[str] = None
    ) -> Dict[str, any]:
        """
        完整查詢擴充
        
        Args:
            query: 原始查詢
            symptoms: 提取的症狀列表（可選）
            
        Returns:
            {
                "original": 原始查詢,
                "expanded": 擴充後查詢,
                "tokens": [擴充詞項列表],
                "negations": [否定詞綁定],
                "mappings": {詞項: [映射詞]}
            }
        """
        result = {
            "original": query,
            "expanded": "",
            "tokens": [],
            "negations": [],
            "mappings": {}
        }
        
        # 1. 否定詞綁定
        if self.config.enable_negation_binding:
            bound_query, negations = self._bind_negations(query)
            result["negations"] = negations
        else:
            bound_query = query
        
        # 2. 提取症狀（如果未提供）
        if symptoms is None:
            symptoms = self._extract_symptoms_from_query(bound_query)
        
        # 3. 構建擴充詞項
        expanded_tokens = []
        
        for symptom in symptoms:
            # 原詞（重複 N 次）
            expanded_tokens.extend([symptom] * self.config.original_weight)
            
            # 同義詞擴充
            if self.config.enable_synonym:
                synonyms = self.synonym_map.get(symptom, [])
                for syn in synonyms:
                    expanded_tokens.extend([syn] * self.config.synonym_weight)
                    
                if synonyms:
                    result["mappings"][symptom] = {
                        "type": "synonym",
                        "terms": synonyms
                    }
            
            # 中醫映射擴充
            if self.config.enable_tcm_mapping:
                mappings = self.tcm_mapping.get(symptom, [])
                for mapping in mappings:
                    expanded_tokens.extend([mapping] * self.config.mapping_weight)
                    
                if mappings:
                    if symptom in result["mappings"]:
                        result["mappings"][symptom]["tcm_terms"] = mappings
                    else:
                        result["mappings"][symptom] = {
                            "type": "tcm",
                            "terms": mappings
                        }
        
        # 4. 構建擴充查詢
        result["tokens"] = expanded_tokens
        result["expanded"] = " ".join(expanded_tokens)
        
        logger.info(f"🔍 查詢擴充:")
        logger.info(f"   原始: {query[:50]}...")
        logger.info(f"   症狀數: {len(symptoms)}")
        logger.info(f"   擴充詞項數: {len(expanded_tokens)}")
        logger.info(f"   否定綁定: {len(result['negations'])} 個")
        logger.info(f"   映射: {len(result['mappings'])} 個")
        
        return result
    
    # ==================== 否定詞綁定 ====================
    def _bind_negations(self, text: str) -> Tuple[str, List[str]]:
        """
        綁定否定詞與後續詞項
        
        例如：「無咳嗽」→「無_咳嗽」
        
        Returns:
            (綁定後文本, [否定詞組列表])
        """
        bound_text = text
        negations = []
        
        # 否定模式：否定詞 + 1-4個字的症狀
        pattern = r'(' + '|'.join(self.negation_words) + r')([^\s，。；]{1,4})'
        
        matches = re.finditer(pattern, text)
        
        for match in matches:
            negation = match.group(1)
            symptom = match.group(2)
            
            # 構建綁定詞
            bound_term = f"{negation}_{symptom}"
            negations.append(bound_term)
            
            # 替換原文本
            bound_text = bound_text.replace(
                match.group(0),
                bound_term
            )
        
        if negations:
            logger.debug(f"   否定詞綁定: {negations}")
        
        return bound_text, negations
    
    # ==================== 程度詞綁定 ====================
    def _bind_degrees(self, text: str) -> Tuple[str, List[str]]:
        """
        綁定程度詞與症狀
        
        例如：「很口乾」→「很_口乾」
        """
        bound_text = text
        degree_terms = []
        
        # 程度詞模式
        pattern = r'(' + '|'.join(self.degree_words) + r')([^\s，。；]{1,4})'
        
        matches = re.finditer(pattern, text)
        
        for match in matches:
            degree = match.group(1)
            symptom = match.group(2)
            
            bound_term = f"{degree}_{symptom}"
            degree_terms.append(bound_term)
            
            bound_text = bound_text.replace(
                match.group(0),
                bound_term
            )
        
        return bound_text, degree_terms
    
    # ==================== 症狀提取 ====================
    def _extract_symptoms_from_query(self, query: str) -> List[str]:
        """從查詢中提取症狀關鍵詞"""
        symptoms = []
        
        # 檢查所有同義詞映射中的關鍵詞
        all_keywords = set(self.synonym_map.keys())
        for synonyms in self.synonym_map.values():
            all_keywords.update(synonyms)
        
        # 檢查中醫映射中的關鍵詞
        all_keywords.update(self.tcm_mapping.keys())
        
        # 查找匹配
        for keyword in all_keywords:
            if keyword in query:
                symptoms.append(keyword)
        
        return symptoms
    
    # ==================== 同義詞查詢 ====================
    def get_synonyms(self, term: str) -> List[str]:
        """獲取詞項的同義詞"""
        # 直接查找
        if term in self.synonym_map:
            return self.synonym_map[term]
        
        # 反向查找
        for key, synonyms in self.synonym_map.items():
            if term in synonyms:
                return [key] + [s for s in synonyms if s != term]
        
        return []
    
    def get_tcm_mappings(self, term: str) -> List[str]:
        """獲取詞項的中醫映射"""
        return self.tcm_mapping.get(term, [])
    
    # ==================== 添加自定義映射 ====================
    def add_synonym(self, term: str, synonyms: List[str]):
        """添加同義詞映射"""
        if term in self.synonym_map:
            self.synonym_map[term].extend(synonyms)
            self.synonym_map[term] = list(set(self.synonym_map[term]))
        else:
            self.synonym_map[term] = synonyms
        
        logger.info(f"➕ 添加同義詞映射: {term} → {synonyms}")
    
    def add_tcm_mapping(self, term: str, mappings: List[str]):
        """添加中醫映射"""
        if term in self.tcm_mapping:
            self.tcm_mapping[term].extend(mappings)
            self.tcm_mapping[term] = list(set(self.tcm_mapping[term]))
        else:
            self.tcm_mapping[term] = mappings
        
        logger.info(f"➕ 添加中醫映射: {term} → {mappings}")