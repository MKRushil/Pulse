# -*- coding: utf-8 -*-
"""
文本處理器
"""

import re
import os
from typing import List, Set, Dict, Any
from pathlib import Path

try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

from ..config import TextProcessorConfig
from .logger import get_logger

logger = get_logger("TextProcessor")

class TextProcessor:
    """文本處理器"""
    
    def __init__(self, config: TextProcessorConfig):
        self.config = config
        self.stopwords = set(config.stopwords)
        self.tcm_keywords = set(config.tcm_keywords)
        
        # 初始化 jieba
        if JIEBA_AVAILABLE:
            self._init_jieba()
        else:
            logger.warning("jieba 未安裝，使用簡單分詞")
    
    def _init_jieba(self):
        """初始化 jieba 分詞器"""
        
        dict_path = self.config.jieba_dict_path
        
        if dict_path:
            if isinstance(dict_path, str):
                dict_path = Path(dict_path)
            
            if dict_path.exists():
                try:
                    # ✅ 使用 context manager 避免 ResourceWarning
                    word_count = 0
                    with open(dict_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            parts = line.split()
                            if len(parts) >= 2:
                                word, freq = parts[0], int(parts[1])
                                jieba.add_word(word, freq=freq)
                                word_count += 1
                            elif len(parts) == 1:
                                jieba.add_word(parts[0], freq=1000)
                                word_count += 1
                    
                    logger.info(f"✅ 載入 jieba 詞典: {word_count} 個詞條")
                    logger.info(f"   詞典路徑: {dict_path}")
                    
                except Exception as e:
                    logger.error(f"❌ 載入詞典失敗: {e}")
                    self._load_default_keywords()
            else:
                logger.warning(f"⚠️  詞典路徑不存在: {dict_path}")
                self._load_default_keywords()
        else:
            logger.info("ℹ️  未指定詞典路徑")
            self._load_default_keywords()

    def _load_default_keywords(self):
        """載入預設 TCM 關鍵詞"""
        for keyword in self.tcm_keywords:
            jieba.add_word(keyword, freq=1000)
        
        if self.tcm_keywords:
            logger.info(f"✅ 已載入 {len(self.tcm_keywords)} 個預設 TCM 關鍵詞")
    
    def segment_text(self, text: str) -> str:
        """分詞處理"""
        
        if not text:
            return ""
        
        # 清理文本
        text = self._clean_text(text)
        
        # 分詞
        if JIEBA_AVAILABLE:
            tokens = list(jieba.cut(text))
        else:
            tokens = self._simple_tokenize(text)
        
        # 過濾停用詞
        tokens = [
            t for t in tokens 
            if t.strip() and t not in self.stopwords
        ]
        
        return " ".join(tokens)
    
    def extract_keywords(
        self,
        text: str,
        top_k: int = 10,
        with_weight: bool = False
    ) -> List[Any]:
        """提取關鍵詞"""
        
        if not text:
            return []
        
        text = self._clean_text(text)
        
        if JIEBA_AVAILABLE:
            # 使用 TF-IDF 提取
            keywords = jieba.analyse.extract_tags(
                text, 
                topK=top_k,
                withWeight=with_weight
            )
            return keywords
        else:
            # 簡單提取
            return self._extract_tcm_keywords(text)[:top_k]
    
    def extract_symptoms(self, text: str) -> List[str]:
        """提取症狀"""
        
        symptoms = []
        
        # 提取 TCM 症狀
        for symptom in self.tcm_keywords:
            if symptom in text:
                symptoms.append(symptom)
        
        # 提取否定症狀
        negations = self._extract_negations(text)
        symptoms.extend(negations)
        
        return list(set(symptoms))
    
    def _extract_negations(self, text: str) -> List[str]:
        """提取否定表述"""
        
        negations = []
        pattern = self.config.negation_pattern
        
        matches = re.finditer(pattern, text)
        for match in matches:
            negation = match.group(1)  # 否定詞
            symptom = match.group(2)   # 症狀
            negations.append(f"無{symptom}")
        
        return negations
    
    def _extract_tcm_keywords(self, text: str) -> List[str]:
        """提取 TCM 關鍵詞"""
        
        found = []
        for keyword in self.tcm_keywords:
            if keyword in text:
                # 計算出現次數作為權重
                count = text.count(keyword)
                found.append((keyword, count))
        
        # 按出現次數排序
        found.sort(key=lambda x: x[1], reverse=True)
        
        return [kw for kw, _ in found]
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        
        # 移除多餘空白
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？；：、]', '', text)
        
        # 過濾舌診內容
        if self.config.ignore_tongue:
            text = self._remove_tongue_content(text)
        
        return text.strip()
    
    def _remove_tongue_content(self, text: str) -> str:
        """移除舌診內容"""
        
        # 舌診相關模式
        tongue_patterns = [
            r'舌[質体]?[紅淡暗紫胖瘦嫩老薄厚潤燥膩腐剝裂齒痕]+',
            r'苔[色質]?[白黃灰黑厚薄膩腐潤燥剝]+',
            r'舌[邊尖根中][有無]?[瘀點瘀斑瘀紫]+',
        ]
        
        for pattern in tongue_patterns:
            text = re.sub(pattern, '', text)
        
        return text
    
    def _simple_tokenize(self, text: str) -> List[str]:
        """簡單分詞（fallback）"""
        
        # 按標點和空格分割
        tokens = re.split(r'[，。！？；：、\s]+', text)
        
        # 進一步分割長詞
        result = []
        for token in tokens:
            if len(token) <= 4:
                result.append(token)
            else:
                # 簡單的2-gram分割
                for i in range(0, len(token) - 1):
                    result.append(token[i:i+2])
        
        return [t for t in result if t]
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """計算文本相似度"""
        
        # 分詞
        tokens1 = set(self.segment_text(text1).split())
        tokens2 = set(self.segment_text(text2).split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard 相似度
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union) if union else 0.0