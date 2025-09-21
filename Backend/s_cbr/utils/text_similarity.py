"""
文本相似度計算工具 v2.0

提供中文文本相似度計算與語義分析
支援多種相似度演算法與優化

版本：v2.0 - 螺旋互動版
更新：優化中文文本相似度演算法
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import logging
import re
import math
from collections import Counter

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    # 中文分詞工具（如果可用）
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    JIEBA_AVAILABLE = False
    jieba = None

try:
    # 向量化工具（如果可用）
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None

class TextSimilarity:
    """
    文本相似度計算器 v2.0
    
    v2.0 特色：
    - 優化的中文文本處理
    - 多種相似度演算法支援
    - 語義相似度計算
    - 領域特定詞彙處理
    """
    
    def __init__(self):
        """初始化文本相似度計算器 v2.0"""
        self.logger = SpiralLogger.get_logger("TextSimilarity") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("TextSimilarity")
        self.version = "2.0"
        
        # 初始化中文分詞
        self.jieba_initialized = False
        if JIEBA_AVAILABLE:
            self._initialize_jieba()
        
        # 中醫專業詞彙庫
        self.tcm_vocabulary = self._load_tcm_vocabulary()
        
        # 停用詞表
        self.stopwords = self._load_stopwords()
        
        # TF-IDF 向量化器（如果可用）
        self.tfidf_vectorizer = None
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,  # 使用自定義停用詞
                ngram_range=(1, 2)
            )
        
        self.logger.info(f"文本相似度計算器 v{self.version} 初始化完成")
    
    def _initialize_jieba(self):
        """初始化結巴分詞"""
        if not JIEBA_AVAILABLE:
            return
        
        try:
            # 載入中醫專業詞典
            jieba.load_userdict(self._get_tcm_dict_path())
            
            # 設置分詞模式
            jieba.enable_paddle()  # 啟用paddle模式（如果可用）
            
            self.jieba_initialized = True
            self.logger.info("結巴分詞初始化完成")
            
        except Exception as e:
            self.logger.warning(f"結巴分詞初始化失敗，使用基礎模式: {str(e)}")
            self.jieba_initialized = False
    
    def calculate_similarity(self, text1: str, text2: str, method: str = "hybrid") -> float:
        """
        計算兩個文本的相似度
        
        Args:
            text1: 第一個文本
            text2: 第二個文本
            method: 計算方法 ("jaccard", "cosine", "semantic", "hybrid")
            
        Returns:
            float: 相似度分數 (0.0-1.0)
        """
        try:
            if not text1 or not text2:
                return 0.0
            
            # 預處理文本
            processed_text1 = self.preprocess_text(text1)
            processed_text2 = self.preprocess_text(text2)
            
            if method == "jaccard":
                return self.jaccard_similarity(processed_text1, processed_text2)
            elif method == "cosine":
                return self.cosine_similarity(processed_text1, processed_text2)
            elif method == "semantic":
                return self.calculate_semantic_similarity(processed_text1, processed_text2)
            elif method == "hybrid":
                return self.hybrid_similarity(processed_text1, processed_text2)
            else:
                self.logger.warning(f"未知的相似度方法: {method}，使用hybrid方法")
                return self.hybrid_similarity(processed_text1, processed_text2)
                
        except Exception as e:
            self.logger.error(f"計算文本相似度失敗: {str(e)}")
            return 0.0
    
    def preprocess_text(self, text: str) -> str:
        """
        文本預處理
        
        Args:
            text: 原始文本
            
        Returns:
            str: 預處理後的文本
        """
        try:
            # 去除HTML標籤和特殊字符
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', text)
            
            # 去除多餘空白
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 轉換為小寫（對於英文部分）
            text = text.lower()
            
            return text
            
        except Exception as e:
            self.logger.error(f"文本預處理失敗: {str(e)}")
            return text
    
    def tokenize_chinese(self, text: str) -> List[str]:
        """
        中文文本分詞
        
        Args:
            text: 中文文本
            
        Returns:
            List[str]: 分詞結果
        """
        try:
            if JIEBA_AVAILABLE and self.jieba_initialized:
                # 使用結巴分詞
                tokens = list(jieba.cut(text, cut_all=False))
            else:
                # 降級：簡單的字符分割
                tokens = self._simple_chinese_tokenize(text)
            
            # 過濾停用詞和短詞
            filtered_tokens = [
                token for token in tokens
                if len(token) > 1 and token not in self.stopwords
            ]
            
            return filtered_tokens
            
        except Exception as e:
            self.logger.error(f"中文分詞失敗: {str(e)}")
            return text.split()
    
    def _simple_chinese_tokenize(self, text: str) -> List[str]:
        """
        簡單的中文分詞（降級方案）
        
        Args:
            text: 中文文本
            
        Returns:
            List[str]: 分詞結果
        """
        # 基於中醫詞彙進行簡單匹配
        tokens = []
        i = 0
        
        while i < len(text):
            matched = False
            
            # 嘗試匹配中醫詞彙（從長到短）
            for length in range(min(6, len(text) - i), 0, -1):
                substring = text[i:i + length]
                if substring in self.tcm_vocabulary or length == 1:
                    tokens.append(substring)
                    i += length
                    matched = True
                    break
            
            if not matched:
                i += 1
        
        return tokens
    
    def jaccard_similarity(self, text1: str, text2: str) -> float:
        """
        計算Jaccard相似度
        
        Args:
            text1: 第一個文本
            text2: 第二個文本
            
        Returns:
            float: Jaccard相似度
        """
        try:
            tokens1 = set(self.tokenize_chinese(text1))
            tokens2 = set(self.tokenize_chinese(text2))
            
            if not tokens1 and not tokens2:
                return 1.0
            
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"計算Jaccard相似度失敗: {str(e)}")
            return 0.0
    
    def cosine_similarity(self, text1: str, text2: str) -> float:
        """
        計算餘弦相似度
        
        Args:
            text1: 第一個文本
            text2: 第二個文本
            
        Returns:
            float: 餘弦相似度
        """
        try:
            if SKLEARN_AVAILABLE:
                return self._sklearn_cosine_similarity(text1, text2)
            else:
                return self._manual_cosine_similarity(text1, text2)
                
        except Exception as e:
            self.logger.error(f"計算餘弦相似度失敗: {str(e)}")
            return 0.0
    
    def _sklearn_cosine_similarity(self, text1: str, text2: str) -> float:
        """使用sklearn計算餘弦相似度"""
        try:
            # 分詞並重新組合
            tokens1 = self.tokenize_chinese(text1)
            tokens2 = self.tokenize_chinese(text2)
            
            processed_text1 = ' '.join(tokens1)
            processed_text2 = ' '.join(tokens2)
            
            # TF-IDF向量化
            tfidf_matrix = self.tfidf_vectorizer.fit_transform([processed_text1, processed_text2])
            
            # 計算餘弦相似度
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            return float(similarity_matrix[0, 1])
            
        except Exception as e:
            self.logger.error(f"sklearn餘弦相似度計算失敗: {str(e)}")
            return self._manual_cosine_similarity(text1, text2)
    
    def _manual_cosine_similarity(self, text1: str, text2: str) -> float:
        """手動計算餘弦相似度"""
        try:
            tokens1 = self.tokenize_chinese(text1)
            tokens2 = self.tokenize_chinese(text2)
            
            # 創建詞頻向量
            all_tokens = set(tokens1 + tokens2)
            
            if not all_tokens:
                return 0.0
            
            vector1 = [tokens1.count(token) for token in all_tokens]
            vector2 = [tokens2.count(token) for token in all_tokens]
            
            # 計算點積
            dot_product = sum(a * b for a, b in zip(vector1, vector2))
            
            # 計算向量的模
            magnitude1 = math.sqrt(sum(a * a for a in vector1))
            magnitude2 = math.sqrt(sum(b * b for b in vector2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception as e:
            self.logger.error(f"手動餘弦相似度計算失敗: {str(e)}")
            return 0.0
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        計算語義相似度 v2.0
        
        Args:
            text1: 第一個文本
            text2: 第二個文本
            
        Returns:
            float: 語義相似度
        """
        try:
            # 分詞
            tokens1 = self.tokenize_chinese(text1)
            tokens2 = self.tokenize_chinese(text2)
            
            if not tokens1 or not tokens2:
                return 0.0
            
            # 中醫語義相似度計算
            semantic_score = self._calculate_tcm_semantic_similarity(tokens1, tokens2)
            
            # 結合字面相似度
            literal_score = self.jaccard_similarity(text1, text2)
            
            # 加權組合
            final_score = semantic_score * 0.7 + literal_score * 0.3
            
            return min(final_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"計算語義相似度失敗: {str(e)}")
            return 0.0
    
    def _calculate_tcm_semantic_similarity(self, tokens1: List[str], tokens2: List[str]) -> float:
        """
        計算中醫語義相似度
        
        Args:
            tokens1: 第一組詞語
            tokens2: 第二組詞語
            
        Returns:
            float: 語義相似度
        """
        try:
            # 提取中醫概念
            tcm_concepts1 = self._extract_tcm_concepts(tokens1)
            tcm_concepts2 = self._extract_tcm_concepts(tokens2)
            
            if not tcm_concepts1 or not tcm_concepts2:
                return 0.0
            
            # 計算概念相似度
            concept_similarity = self._calculate_concept_similarity(tcm_concepts1, tcm_concepts2)
            
            return concept_similarity
            
        except Exception as e:
            self.logger.error(f"計算中醫語義相似度失敗: {str(e)}")
            return 0.0
    
    def _extract_tcm_concepts(self, tokens: List[str]) -> Dict[str, List[str]]:
        """
        提取中醫概念
        
        Args:
            tokens: 詞語列表
            
        Returns:
            Dict[str, List[str]]: 概念分類
        """
        concepts = {
            "symptoms": [],      # 症狀
            "syndromes": [],     # 證候  
            "organs": [],        # 臟腑
            "substances": [],    # 氣血津液
            "treatments": [],    # 治法
            "herbs": [],         # 藥物
            "pulse": []          # 脈象
        }
        
        try:
            for token in tokens:
                if token in self.tcm_vocabulary:
                    category = self.tcm_vocabulary[token].get("category", "general")
                    if category in concepts:
                        concepts[category].append(token)
                        
            return concepts
            
        except Exception as e:
            self.logger.error(f"提取中醫概念失敗: {str(e)}")
            return concepts
    
    def _calculate_concept_similarity(self, concepts1: Dict[str, List[str]], concepts2: Dict[str, List[str]]) -> float:
        """
        計算概念相似度
        
        Args:
            concepts1: 第一組概念
            concepts2: 第二組概念
            
        Returns:
            float: 概念相似度
        """
        try:
            total_similarity = 0.0
            category_count = 0
            
            # 概念類別權重
            category_weights = {
                "symptoms": 0.25,
                "syndromes": 0.20,
                "organs": 0.15,
                "substances": 0.15,
                "treatments": 0.10,
                "herbs": 0.10,
                "pulse": 0.05
            }
            
            for category, weight in category_weights.items():
                set1 = set(concepts1.get(category, []))
                set2 = set(concepts2.get(category, []))
                
                if set1 or set2:
                    # 計算該類別的Jaccard相似度
                    intersection = len(set1 & set2)
                    union = len(set1 | set2)
                    category_similarity = intersection / union if union > 0 else 0.0
                    
                    total_similarity += category_similarity * weight
                    category_count += weight
            
            return total_similarity / category_count if category_count > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"計算概念相似度失敗: {str(e)}")
            return 0.0
    
    def hybrid_similarity(self, text1: str, text2: str) -> float:
        """
        混合相似度計算
        
        Args:
            text1: 第一個文本
            text2: 第二個文本
            
        Returns:
            float: 混合相似度
        """
        try:
            # 計算各種相似度
            jaccard_score = self.jaccard_similarity(text1, text2)
            cosine_score = self.cosine_similarity(text1, text2)
            semantic_score = self.calculate_semantic_similarity(text1, text2)
            
            # 加權組合
            weights = {
                "jaccard": 0.3,
                "cosine": 0.4,
                "semantic": 0.3
            }
            
            hybrid_score = (
                jaccard_score * weights["jaccard"] +
                cosine_score * weights["cosine"] +
                semantic_score * weights["semantic"]
            )
            
            return min(hybrid_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"計算混合相似度失敗: {str(e)}")
            return 0.0
    
    def calculate_batch_similarity(self, target_text: str, text_list: List[str], method: str = "hybrid") -> List[Tuple[int, float]]:
        """
        批量計算文本相似度
        
        Args:
            target_text: 目標文本
            text_list: 文本列表
            method: 計算方法
            
        Returns:
            List[Tuple[int, float]]: (索引, 相似度) 列表，按相似度降序排列
        """
        try:
            similarities = []
            
            for i, text in enumerate(text_list):
                similarity = self.calculate_similarity(target_text, text, method)
                similarities.append((i, similarity))
            
            # 按相似度降序排列
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities
            
        except Exception as e:
            self.logger.error(f"批量計算相似度失敗: {str(e)}")
            return []
    
    def _load_tcm_vocabulary(self) -> Dict[str, Dict[str, Any]]:
        """載入中醫詞彙庫"""
        try:
            # 簡化的中醫詞彙庫
            vocabulary = {
                # 症狀
                "頭痛": {"category": "symptoms", "weight": 1.0},
                "失眠": {"category": "symptoms", "weight": 1.0},
                "疲勞": {"category": "symptoms", "weight": 1.0},
                "心悸": {"category": "symptoms", "weight": 1.0},
                "胸悶": {"category": "symptoms", "weight": 1.0},
                "腹脹": {"category": "symptoms", "weight": 1.0},
                "便秘": {"category": "symptoms", "weight": 1.0},
                "腹瀉": {"category": "symptoms", "weight": 1.0},
                
                # 證候
                "氣虛": {"category": "syndromes", "weight": 1.0},
                "血瘀": {"category": "syndromes", "weight": 1.0},
                "陰虛": {"category": "syndromes", "weight": 1.0},
                "陽虛": {"category": "syndromes", "weight": 1.0},
                "氣滯": {"category": "syndromes", "weight": 1.0},
                "痰濕": {"category": "syndromes", "weight": 1.0},
                "肝鬱氣滯": {"category": "syndromes", "weight": 1.0},
                "心神不寧": {"category": "syndromes", "weight": 1.0},
                "脾胃虛弱": {"category": "syndromes", "weight": 1.0},
                
                # 臟腑
                "心": {"category": "organs", "weight": 1.0},
                "肝": {"category": "organs", "weight": 1.0},
                "脾": {"category": "organs", "weight": 1.0},
                "肺": {"category": "organs", "weight": 1.0},
                "腎": {"category": "organs", "weight": 1.0},
                "胃": {"category": "organs", "weight": 1.0},
                "膽": {"category": "organs", "weight": 1.0},
                
                # 脈象
                "浮脈": {"category": "pulse", "weight": 1.0},
                "沉脈": {"category": "pulse", "weight": 1.0},
                "弦脈": {"category": "pulse", "weight": 1.0},
                "細脈": {"category": "pulse", "weight": 1.0},
                "數脈": {"category": "pulse", "weight": 1.0},
                "遲脈": {"category": "pulse", "weight": 1.0},
                "滑脈": {"category": "pulse", "weight": 1.0},
                "澀脈": {"category": "pulse", "weight": 1.0},
                
                # 治法
                "疏肝": {"category": "treatments", "weight": 1.0},
                "解鬱": {"category": "treatments", "weight": 1.0},
                "養心": {"category": "treatments", "weight": 1.0},
                "安神": {"category": "treatments", "weight": 1.0},
                "健脾": {"category": "treatments", "weight": 1.0},
                "益氣": {"category": "treatments", "weight": 1.0},
                "補腎": {"category": "treatments", "weight": 1.0},
                "滋陰": {"category": "treatments", "weight": 1.0},
                
                # 藥物
                "柴胡": {"category": "herbs", "weight": 1.0},
                "當歸": {"category": "herbs", "weight": 1.0},
                "白芍": {"category": "herbs", "weight": 1.0},
                "甘草": {"category": "herbs", "weight": 1.0},
                "人參": {"category": "herbs", "weight": 1.0},
                "黃芪": {"category": "herbs", "weight": 1.0},
                "地黃": {"category": "herbs", "weight": 1.0}
            }
            
            return vocabulary
            
        except Exception as e:
            self.logger.error(f"載入中醫詞彙庫失敗: {str(e)}")
            return {}
    
    def _load_stopwords(self) -> set:
        """載入停用詞表"""
        try:
            # 中文停用詞
            stopwords = {
                "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", 
                "都", "一", "一個", "上", "也", "很", "到", "說", "要", "去",
                "你", "會", "著", "沒有", "看", "好", "自己", "這", "那", "時",
                "來", "用", "們", "生", "大", "為", "能", "作", "地", "於"
            }
            
            return stopwords
            
        except Exception as e:
            self.logger.error(f"載入停用詞失敗: {str(e)}")
            return set()
    
    def _get_tcm_dict_path(self) -> Optional[str]:
        """獲取中醫詞典路徑"""
        # 實際應用中，這應該是一個真實的詞典文件路徑
        return None
    
    def get_similarity_stats(self) -> Dict[str, Any]:
        """
        獲取相似度計算統計
        
        Returns:
            Dict[str, Any]: 統計信息
        """
        try:
            return {
                "version": self.version,
                "jieba_available": JIEBA_AVAILABLE,
                "sklearn_available": SKLEARN_AVAILABLE,
                "jieba_initialized": self.jieba_initialized,
                "tcm_vocabulary_size": len(self.tcm_vocabulary),
                "stopwords_size": len(self.stopwords),
                "supported_methods": ["jaccard", "cosine", "semantic", "hybrid"],
                "default_method": "hybrid"
            }
            
        except Exception as e:
            self.logger.error(f"獲取統計信息失敗: {str(e)}")
            return {"error": str(e), "version": self.version}

# 便捷函數
def calculate_text_similarity(text1: str, text2: str, method: str = "hybrid") -> float:
    """
    便捷函數：計算文本相似度
    
    Args:
        text1: 第一個文本
        text2: 第二個文本
        method: 計算方法
        
    Returns:
        float: 相似度分數
    """
    similarity_calculator = TextSimilarity()
    return similarity_calculator.calculate_similarity(text1, text2, method)

def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    便捷函數：計算語義相似度
    
    Args:
        text1: 第一個文本
        text2: 第二個文本
        
    Returns:
        float: 語義相似度分數
    """
    similarity_calculator = TextSimilarity()
    return similarity_calculator.calculate_semantic_similarity(text1, text2)

# 向後兼容的類別名稱
TextSimilarityV2 = TextSimilarity

__all__ = [
    "TextSimilarity", "TextSimilarityV2", 
    "calculate_text_similarity", "calculate_semantic_similarity"
]