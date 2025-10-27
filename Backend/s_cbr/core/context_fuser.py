# -*- coding: utf-8 -*-
"""
Patient Context Fusion
統一處理增量合併、去重、否定規則化、權重釘選
"""

from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger("ContextFuser")

class ContextFuser:
    """上下文融合器"""
    
    def __init__(self, config=None):
        self.config = config
        self.pin_threshold = 0.8  # 釘選閾值
        self.negation_patterns = ["無", "沒有", "不", "未"]
        logger.info("✅ Context Fuser 初始化")
    
    def update(
        self,
        prev_ctx: Dict[str, Any],
        new_ctx: Dict[str, Any],
        round_num: int = 1
    ) -> Dict[str, Any]:
        """
        更新並融合患者上下文
        
        Args:
            prev_ctx: 前一輪上下文
            new_ctx: 新輸入上下文
            round_num: 當前輪次
            
        Returns:
            融合後的上下文
        """
        fused = {
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "symptoms": [],
            "negated_symptoms": [],
            "key_signs": [],
            "pinned_terms": [],
            "symptom_sources": defaultdict(list),  # 症狀來源追蹤
            "intensity_map": {},  # 症狀強度映射
            "history": []
        }
        
        # Step 1: 合併症狀列表
        prev_symptoms = set(prev_ctx.get("symptoms", []))
        new_symptoms = set(self._extract_symptoms(new_ctx))
        
        # Step 2: 處理否定症狀
        new_negated = self._process_negations(new_ctx)
        prev_negated = set(prev_ctx.get("negated_symptoms", []))
        
        # 移除被否定的症狀
        for neg in new_negated:
            base_symptom = neg.replace("無_", "")
            prev_symptoms.discard(base_symptom)
            new_symptoms.discard(base_symptom)
        
        # Step 3: 合併並去重
        all_symptoms = prev_symptoms | new_symptoms
        all_negated = prev_negated | new_negated
        
        # Step 4: 記錄症狀來源
        for symptom in new_symptoms:
            fused["symptom_sources"][symptom].append(round_num)
        
        for symptom in prev_symptoms:
            sources = prev_ctx.get("symptom_sources", {}).get(symptom, [])
            fused["symptom_sources"][symptom].extend(sources)
        
        # Step 5: 識別關鍵症狀（釘選）
        key_signs = self._identify_key_signs(
            all_symptoms,
            fused["symptom_sources"]
        )
        
        # Step 6: 提取強度信息
        intensity_map = self._extract_intensity(new_ctx)
        if prev_ctx.get("intensity_map"):
            intensity_map.update(prev_ctx["intensity_map"])
        
        # Step 7: 組裝融合結果
        fused.update({
            "symptoms": sorted(list(all_symptoms)),
            "negated_symptoms": sorted(list(all_negated)),
            "key_signs": key_signs,
            "pinned_terms": self._get_pinned_terms(key_signs, round_num),
            "intensity_map": intensity_map,
            "accumulated_question": self._merge_questions(
                prev_ctx.get("accumulated_question", ""),
                new_ctx.get("question", "")
            )
        })
        
        # Step 8: 保存歷史
        if prev_ctx.get("history"):
            fused["history"] = prev_ctx["history"][-5:]  # 保留最近5輪
        fused["history"].append({
            "round": round_num,
            "new_symptoms": list(new_symptoms),
            "negated": list(new_negated)
        })
        
        logger.info(f"🔄 Context Fusion 完成 [Round {round_num}]")
        logger.info(f"   症狀數: {len(all_symptoms)}, 否定數: {len(all_negated)}")
        logger.info(f"   關鍵症狀: {key_signs[:3]}")
        
        return fused
    
    def _extract_symptoms(self, ctx: Dict) -> List[str]:
        """提取症狀"""
        symptoms = []
        
        # 從多個可能欄位提取
        for field in ["symptoms", "symptom_list", "chief_complaint"]:
            if field in ctx:
                value = ctx[field]
                if isinstance(value, list):
                    symptoms.extend(value)
                elif isinstance(value, str):
                    # 簡單分詞
                    symptoms.extend(self._tokenize_symptoms(value))
        
        return symptoms
    
    def _process_negations(self, ctx: Dict) -> Set[str]:
        """處理否定症狀"""
        negated = set()
        text = ctx.get("question", "") + " " + ctx.get("text", "")
        
        for neg_word in self.negation_patterns:
            # 簡單的否定模式匹配
            import re
            pattern = f"{neg_word}([^，。；]{1,4})"
            matches = re.findall(pattern, text)
            for match in matches:
                negated.add(f"無_{match}")
        
        return negated
    
    def _identify_key_signs(
        self,
        symptoms: Set[str],
        sources: Dict[str, List[int]]
    ) -> List[str]:
        """
        識別關鍵症狀
        - 多輪重複出現
        - 高頻症狀
        - 特定重要症狀
        """
        key_signs = []
        
        # 重要症狀關鍵詞
        important_keywords = {
            "失眠", "心悸", "頭暈", "胸悶", "腹痛",
            "發熱", "咳嗽", "腰痠", "耳鳴", "盜汗"
        }
        
        # 計算症狀重要性分數
        symptom_scores = {}
        for symptom in symptoms:
            score = 0.0
            
            # 出現頻率
            frequency = len(sources.get(symptom, []))
            score += frequency * 0.3
            
            # 是否為重要症狀
            if symptom in important_keywords:
                score += 0.5
            
            # 是否跨輪出現
            rounds = set(sources.get(symptom, []))
            if len(rounds) > 1:
                score += 0.2
            
            symptom_scores[symptom] = score
        
        # 排序並選擇前N個
        sorted_symptoms = sorted(
            symptom_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        key_signs = [s[0] for s in sorted_symptoms[:5]]
        
        return key_signs
    
    def _get_pinned_terms(
        self,
        key_signs: List[str],
        round_num: int
    ) -> List[str]:
        """
        獲取釘選詞（必須在後續檢索中包含）
        """
        pinned = []
        
        # 前3個關鍵症狀必定釘選
        pinned.extend(key_signs[:3])
        
        # 如果是後期輪次，釘選更多
        if round_num >= 3:
            pinned.extend(key_signs[3:5])
        
        return pinned
    
    def _extract_intensity(self, ctx: Dict) -> Dict[str, str]:
        """
        提取症狀強度
        輕度/中度/重度/極重
        """
        intensity_map = {}
        text = ctx.get("question", "") + " " + ctx.get("text", "")
        
        intensity_patterns = {
            "輕微": "輕度",
            "稍微": "輕度",
            "有點": "輕度",
            "比較": "中度",
            "很": "重度",
            "非常": "重度",
            "極": "極重",
            "嚴重": "重度"
        }
        
        for pattern, level in intensity_patterns.items():
            import re
            matches = re.findall(f"{pattern}([^，。；]{1,4})", text)
            for match in matches:
                intensity_map[match] = level
        
        return intensity_map
    
    def _tokenize_symptoms(self, text: str) -> List[str]:
        """簡單症狀分詞"""
        # 使用標點分割
        import re
        tokens = re.split(r'[，。、；\s]+', text)
        
        # 過濾短詞
        valid_tokens = [
            t for t in tokens
            if len(t) >= 2 and len(t) <= 4
        ]
        
        return valid_tokens
    
    def _merge_questions(self, prev_q: str, new_q: str) -> str:
        """合併問題文本"""
        if not prev_q:
            return new_q
        if not new_q:
            return prev_q
        
        # 避免重複
        if new_q in prev_q:
            return prev_q
        
        return f"{prev_q} {new_q}".strip()
    
    def get_retrieval_query(self, fused_ctx: Dict) -> str:
        """
        生成檢索查詢（包含釘選詞）
        """
        query_parts = []
        
        # 1. 釘選詞必須包含（重複3次提高權重）
        pinned = fused_ctx.get("pinned_terms", [])
        for term in pinned:
            query_parts.extend([term] * 3)
        
        # 2. 關鍵症狀（重複2次）
        key_signs = fused_ctx.get("key_signs", [])
        for sign in key_signs:
            if sign not in pinned:
                query_parts.extend([sign] * 2)
        
        # 3. 其他症狀（1次）
        other_symptoms = fused_ctx.get("symptoms", [])
        for symptom in other_symptoms:
            if symptom not in pinned and symptom not in key_signs:
                query_parts.append(symptom)
        
        # 4. 否定症狀（明確標記）
        negated = fused_ctx.get("negated_symptoms", [])
        for neg in negated:
            query_parts.append(neg)
        
        return " ".join(query_parts)