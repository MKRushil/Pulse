# -*- coding: utf-8 -*-
"""
證型轉化器 - 基於新條件動態調整證型
"""

from typing import Dict, List, Any, Tuple, Optional
import yaml
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger("PatternShifter")

class PatternShifter:
    """證型轉化檢測器"""
    
    def __init__(self, rules_path: Path = None):
        """載入轉化規則"""
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "knowledge" / "pattern_transitions.yaml"
        
        # 如果檔案存在則載入，否則使用內建規則
        if rules_path.exists():
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.rules = yaml.safe_load(f)
        else:
            self.rules = self._get_default_rules()
        
        logger.info(f"✅ 證型轉化器初始化: {len(self.rules.get('transitions', []))} 條規則")
    
    def check_transition(
        self,
        current_pattern: str,
        new_symptoms: List[str],
        accumulated_symptoms: List[str],
        round_num: int
    ) -> Tuple[bool, Optional[str], str]:
        """
        檢查是否需要證型轉化
        
        Args:
            current_pattern: 當前證型
            new_symptoms: 本輪新增症狀
            accumulated_symptoms: 累積所有症狀
            round_num: 當前輪次
        
        Returns:
            (需要轉化, 新證型, 轉化原因)
        """
        
        # 第1輪不轉化
        if round_num == 1:
            return False, None, ""
        
        # 檢查所有轉化規則
        for rule in self.rules.get('transitions', []):
            from_pattern = rule['from']
            to_pattern = rule['to']
            triggers = rule['triggers']
            min_match = rule.get('min_match', 2)
            
            # 檢查是否匹配當前證型
            if from_pattern not in current_pattern:
                continue
            
            # 檢查觸發條件
            matched_triggers = []
            for trigger in triggers:
                if any(trigger in s for s in new_symptoms) or any(trigger in s for s in accumulated_symptoms):
                    matched_triggers.append(trigger)
            
            # 達到最小匹配數
            if len(matched_triggers) >= min_match:
                reason = f"檢測到 {matched_triggers[:3]}，符合轉化條件"
                logger.info(f"🔄 證型轉化: {from_pattern} → {to_pattern}")
                logger.info(f"   原因: {reason}")
                return True, to_pattern, reason
        
        return False, None, ""
    
    def suggest_additional_pattern(
        self,
        primary_pattern: str,
        symptoms: List[str]
    ) -> Optional[str]:
        """建議夾證"""
        
        for rule in self.rules.get('additional_patterns', []):
            main = rule['main']
            additional = rule['additional']
            indicators = rule['indicators']
            min_match = rule.get('min_match', 2)
            
            if main not in primary_pattern:
                continue
            
            matched = sum(1 for ind in indicators if any(ind in s for s in symptoms))
            
            if matched >= min_match:
                logger.info(f"➕ 建議夾證: {additional}")
                return additional
        
        return None
    
    def _get_default_rules(self) -> Dict:
        """內建轉化規則"""
        return {
            "transitions": [
                {
                    "from": "心脾兩虛",
                    "to": "心腎不交",
                    "triggers": ["舌尖紅", "口乾", "五心煩熱", "盜汗", "遺精"],
                    "min_match": 2,
                    "description": "陰虛火旺證候明顯"
                },
                {
                    "from": "心脾兩虛",
                    "to": "心脾兩虛夾陰虛",
                    "triggers": ["舌紅", "少苔", "口乾", "手足心熱"],
                    "min_match": 2,
                    "description": "出現陰虛症狀"
                },
                {
                    "from": "氣虛",
                    "to": "氣血兩虛",
                    "triggers": ["面色萎黃", "唇甲淡白", "頭暈", "心悸"],
                    "min_match": 2,
                    "description": "血虛症狀明顯"
                },
                {
                    "from": "肝鬱",
                    "to": "肝鬱化火",
                    "triggers": ["口苦", "煩躁", "易怒", "脅痛", "舌紅", "苔黃"],
                    "min_match": 3,
                    "description": "鬱而化火"
                }
            ],
            "additional_patterns": [
                {
                    "main": "心脾兩虛",
                    "additional": "夾濕",
                    "indicators": ["苔膩", "胸悶", "身重", "便溏"],
                    "min_match": 2
                },
                {
                    "main": "腎陰虛",
                    "additional": "夾虛火",
                    "indicators": ["五心煩熱", "潮熱", "盜汗", "舌紅少苔"],
                    "min_match": 2
                }
            ]
        }