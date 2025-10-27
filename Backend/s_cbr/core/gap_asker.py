# -*- coding: utf-8 -*-
"""
補問器 - 自動生成關鍵補問
"""

from typing import List, Dict, Any
from ..utils.logger import get_logger

logger = get_logger("GapAsker")

class GapAsker:
    """缺口症狀補問器"""
    
    def __init__(self):
        # 關鍵症狀類別
        self.critical_categories = {
            "tongue": ["舌象", "舌質", "舌苔"],
            "pulse": ["脈象", "脈搏"],
            "sleep": ["睡眠", "失眠", "入睡", "早醒"],
            "sweat": ["汗", "盜汗", "自汗"],
            "appetite": ["食慾", "納", "飲食"],
            "stool": ["大便", "便秘", "腹瀉"],
            "urination": ["小便", "尿"],
            "emotion": ["情緒", "煩躁", "抑鬱"],
        }
        
        # 補問模板
        self.question_templates = {
            "tongue": "請描述舌象（舌質顏色：紅/淡/暗，舌苔：薄白/厚膩/黃膩）",
            "pulse": "請描述脈象（浮/沉、遲/數、滑/澀、弦/細等）",
            "sleep": "睡眠狀況如何？（入睡困難/易醒/早醒/多夢）",
            "sweat": "出汗情況？（自汗/盜汗/無汗）",
            "appetite": "食慾如何？一天幾餐？",
            "stool": "大便情況？（乾/溏/正常，次數）",
            "urination": "小便情況？（頻數/不利/正常）",
            "emotion": "情緒狀態？（易怒/抑鬱/焦慮/正常）",
        }
    
    def generate_questions(
        self,
        accumulated_symptoms: List[str],
        metrics: Dict[str, float],
        round_num: int,
        max_questions: int = 2
    ) -> List[str]:
        """
        生成補問列表
        
        Args:
            accumulated_symptoms: 已累積的症狀
            metrics: 當前評估指標
            round_num: 當前輪次
            max_questions: 最多生成幾個問題
        
        Returns:
            問題列表
        """
        
        # 檢查觸發條件
        should_ask = self._should_generate(metrics)
        
        if not should_ask:
            return []
        
        # 找出缺失的類別
        missing_categories = self._find_missing_categories(accumulated_symptoms)
        
        # 按優先級排序
        prioritized = self._prioritize_categories(missing_categories, round_num)
        
        # 生成問題
        questions = []
        for category in prioritized[:max_questions]:
            template = self.question_templates.get(category)
            if template:
                questions.append(template)
        
        if questions:
            logger.info(f"🔍 生成補問 [{len(questions)}個]:")
            for q in questions:
                logger.info(f"   ❓ {q}")
        
        return questions
    
    def _should_generate(self, metrics: Dict[str, float]) -> bool:
        """判斷是否需要補問"""
        sc = metrics.get('evidence_coverage', metrics.get('SC', 0))
        
        # SC < 0.5 時強制補問
        if sc < 0.5:
            return True
        
        # 語義一致性低時補問
        consistency = metrics.get('semantic_consistency', 1.0)
        if consistency < 0.6:
            return True
        
        return False
    
    def _find_missing_categories(self, symptoms: List[str]) -> List[str]:
        """找出缺失的症狀類別"""
        missing = []
        
        symptoms_text = " ".join(symptoms)
        
        for category, keywords in self.critical_categories.items():
            # 檢查是否已包含該類別
            has_category = any(kw in symptoms_text for kw in keywords)
            
            if not has_category:
                missing.append(category)
        
        return missing
    
    def _prioritize_categories(
        self,
        missing: List[str],
        round_num: int
    ) -> List[str]:
        """按優先級排序缺失類別"""
        
        # 定義優先級（數字越小越重要）
        priority_map = {
            "tongue": 1,  # 舌診最重要
            "pulse": 2,   # 脈診次之
            "sleep": 3,
            "sweat": 4,
            "appetite": 5,
            "stool": 6,
            "urination": 7,
            "emotion": 8,
        }
        
        # 第1輪優先舌脈
        if round_num == 1:
            priority_map["tongue"] = 0
            priority_map["pulse"] = 0
        
        # 排序
        sorted_missing = sorted(
            missing,
            key=lambda cat: priority_map.get(cat, 999)
        )
        
        return sorted_missing