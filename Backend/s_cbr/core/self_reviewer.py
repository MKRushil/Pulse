# -*- coding: utf-8 -*-
"""
自我審稿器 - LLM 輸出品質控制
"""

from typing import Dict, Any, Optional, List
from ..utils.logger import get_logger

logger = get_logger("SelfReviewer")

class SelfReviewer:
    """診斷輸出自我審稿"""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    async def review(
        self,
        current_output: str,
        previous_output: Optional[str],
        new_symptoms: list[str],
        round_num: int
    ) -> Dict[str, Any]:
        """
        審稿當前輸出
        
        Returns:
            {
                "passed": bool,
                "issues": List[str],
                "revised_output": Optional[str]
            }
        """
        
        issues = []
        
        # ==================== 檢查1: 新症狀吸收 ====================
        if new_symptoms:
            new_absorbed = self._check_new_symptom_absorption(current_output, new_symptoms)
            if not new_absorbed:
                issues.append("未吸收新症狀")
        
        # ==================== 檢查2: 內容重複 ====================
        if previous_output:
            repetition_rate = self._calculate_repetition(current_output, previous_output)
            if repetition_rate > 0.3:  # 重複超過30%
                issues.append(f"內容重複率過高 ({repetition_rate:.0%})")
        
        # ==================== 檢查3: 證型是否更新 ====================
        if round_num >= 2 and previous_output and new_symptoms:
            needs_update = self._check_pattern_update_needed(new_symptoms)
            pattern_updated = self._check_pattern_changed(current_output, previous_output)
            
            if needs_update and not pattern_updated:
                issues.append("應根據新症狀調整證型但未調整")
        
        # ==================== 決策 ====================
        passed = len(issues) == 0
        
        if passed:
            logger.info("✅ 自我審稿通過")
            return {
                "passed": True,
                "issues": [],
                "revised_output": None
            }
        else:
            logger.warning(f"⚠️  自我審稿發現問題: {issues}")
            
            # 如果有 LLM，嘗試修正
            if self.llm:
                revised = await self._revise_output(current_output, issues, new_symptoms)
                return {
                    "passed": False,
                    "issues": issues,
                    "revised_output": revised
                }
            else:
                return {
                    "passed": False,
                    "issues": issues,
                    "revised_output": None
                }
    
    def _check_new_symptom_absorption(self, output: str, new_symptoms: List[str]) -> bool:
        """檢查是否吸收新症狀"""
        absorbed_count = sum(1 for symptom in new_symptoms if symptom in output)
        return absorbed_count >= len(new_symptoms) * 0.5  # 至少50%
    
    def _calculate_repetition(self, current: str, previous: str) -> float:
        """計算重複率"""
        # 簡單實作：計算句子重複
        current_sentences = set(current.split('。'))
        previous_sentences = set(previous.split('。'))
        
        if not current_sentences:
            return 0.0
        
        repeated = current_sentences & previous_sentences
        return len(repeated) / len(current_sentences)
    
    def _check_pattern_update_needed(self, new_symptoms: List[str]) -> bool:
        """判斷是否需要更新證型"""
        critical_keywords = ["舌尖紅", "口乾", "五心煩熱", "盜汗", "苔黃", "便秘"]
        matched = sum(1 for kw in critical_keywords if any(kw in s for s in new_symptoms))
        return matched >= 2
    
    def _check_pattern_changed(self, current: str, previous: str) -> bool:
        """檢查證型是否改變"""
        # 提取證型（簡化版）
        import re
        
        pattern_keywords = ["心脾兩虛", "心腎不交", "肝鬱", "氣虛", "陰虛"]
        
        current_pattern = None
        previous_pattern = None
        
        for pk in pattern_keywords:
            if pk in current:
                current_pattern = pk
            if pk in previous:
                previous_pattern = pk
        
        return current_pattern != previous_pattern
    
    async def _revise_output(
        self,
        original: str,
        issues: List[str],
        new_symptoms: List[str]
    ) -> str:
        """使用 LLM 修正輸出"""
        
        review_prompt = f"""
請修正以下診斷輸出的問題：

【原始輸出】
{original}

【發現的問題】
{chr(10).join(f'- {issue}' for issue in issues)}

【本輪新增症狀】
{', '.join(new_symptoms)}

【修正要求】
1. 必須明確提及新增症狀
2. 避免重複上一輪的描述
3. 如有必要，調整證型判斷
4. 保持專業性與簡潔性

請輸出修正後的診斷結果：
"""
        
        try:
            revised = await self.llm.chat_complete(
                system_prompt="你是專業的中醫診斷審稿助手",
                user_prompt=review_prompt,
                temperature=0.2
            )
            
            logger.info("✏️  LLM 修正完成")
            return revised
            
        except Exception as e:
            logger.error(f"修正失敗: {e}")
            return original