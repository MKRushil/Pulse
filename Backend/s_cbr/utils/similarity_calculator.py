"""
相似度計算器 v1.0

v1.0 功能：
- 多種相似度計算算法
- 中醫特徵相似度
- 脈診特徵比較
- 向量化相似度計算

版本：v1.0
"""

from typing import List, Dict, Any, Optional, Union
import math
import re
from collections import Counter

class SimilarityCalculator:
    """
    相似度計算器 v1.0
    
    v1.0 特色：
    - 支援多種相似度算法
    - 中醫專業特徵比較
    - 脈診特殊相似度計算
    - 加權相似度支援
    """
    
    def __init__(self):
        """初始化相似度計算器 v1.0"""
        self.version = "1.0"
        
        # v1.0 中醫專用詞彙權重
        self.tcm_symptom_weights = {
            '頭痛': 1.2, '失眠': 1.1, '疲勞': 1.0, '胸悶': 1.3,
            '咳嗽': 1.2, '腹痛': 1.3, '眩暈': 1.2, '發熱': 1.4,
            '便秘': 1.1, '腹瀉': 1.2, '心悸': 1.3, '多夢': 1.0
        }
        
        # v1.0 脈診特徵權重
        self.pulse_feature_weights = {
            '浮': 1.0, '沉': 1.0, '遲': 1.1, '數': 1.1,
            '滑': 1.2, '澀': 1.2, '弦': 1.3, '緩': 1.0,
            '細': 1.1, '洪': 1.2, '虛': 1.3, '實': 1.3
        }
    
    def calculate_text_similarity(self, text1: str, text2: str, 
                                method: str = "jaccard", 
                                weights: Optional[Dict[str, float]] = None) -> float:
        """
        計算文本相似度
        
        Args:
            text1, text2: 待比較的文本
            method: 計算方法 ("jaccard", "cosine", "weighted_jaccard")
            weights: 詞彙權重字典
            
        Returns:
            相似度分數 (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        # 預處理文本
        words1 = self._preprocess_text(text1)
        words2 = self._preprocess_text(text2)
        
        if not words1 or not words2:
            return 0.0
        
        if method == "jaccard":
            return self._jaccard_similarity(words1, words2)
        elif method == "cosine":
            return self._cosine_similarity(words1, words2)
        elif method == "weighted_jaccard":
            return self._weighted_jaccard_similarity(words1, words2, weights)
        else:
            return self._jaccard_similarity(words1, words2)
    
    def calculate_tcm_symptom_similarity_v1(self, symptoms1: List[str], 
                                           symptoms2: List[str]) -> float:
        """
        計算中醫症狀相似度 v1.0
        
        使用中醫專業詞彙權重進行加權計算
        """
        if not symptoms1 or not symptoms2:
            return 0.0
        
        # 標準化症狀列表
        normalized_symptoms1 = [self._normalize_tcm_term(s) for s in symptoms1]
        normalized_symptoms2 = [self._normalize_tcm_term(s) for s in symptoms2]
        
        # 使用加權 Jaccard 相似度
        return self._weighted_jaccard_similarity(
            normalized_symptoms1, 
            normalized_symptoms2, 
            self.tcm_symptom_weights
        )
    
    def calculate_pulse_similarity_v1(self, pulse1: str, pulse2: str) -> float:
        """
        計算脈診相似度 v1.0
        
        專門針對脈象特徵的相似度計算
        """
        if not pulse1 or not pulse2:
            return 0.0
        
        # 提取脈診特徵
        features1 = self._extract_pulse_features(pulse1)
        features2 = self._extract_pulse_features(pulse2)
        
        if not features1 or not features2:
            return 0.0
        
        # 使用脈診特徵權重計算
        return self._weighted_jaccard_similarity(
            features1, 
            features2, 
            self.pulse_feature_weights
        )
    
    def calculate_age_similarity(self, age1: Union[int, str], age2: Union[int, str], 
                               max_diff: int = 50) -> float:
        """
        計算年齡相似度
        
        Args:
            age1, age2: 年齡值
            max_diff: 最大年齡差異（超過此值相似度為0）
            
        Returns:
            相似度分數 (0-1)
        """
        try:
            age1_num = int(age1) if isinstance(age1, str) else age1
            age2_num = int(age2) if isinstance(age2, str) else age2
            
            diff = abs(age1_num - age2_num)
            if diff >= max_diff:
                return 0.0
            
            return max(0.0, 1.0 - diff / max_diff)
            
        except (ValueError, TypeError):
            return 0.0
    
    def calculate_numeric_similarity(self, val1: float, val2: float, 
                                   max_diff: float = 1.0) -> float:
        """
        計算數值相似度
        
        Args:
            val1, val2: 數值
            max_diff: 最大差異值
            
        Returns:
            相似度分數 (0-1)
        """
        if val1 is None or val2 is None:
            return 0.0
        
        diff = abs(val1 - val2)
        if diff >= max_diff:
            return 0.0
        
        return max(0.0, 1.0 - diff / max_diff)
    
    def calculate_vector_similarity(self, vec1: List[float], vec2: List[float],
                                  method: str = "cosine") -> float:
        """
        計算向量相似度
        
        Args:
            vec1, vec2: 向量
            method: 計算方法 ("cosine", "euclidean", "manhattan")
            
        Returns:
            相似度分數 (0-1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        if method == "cosine":
            return self._cosine_vector_similarity(vec1, vec2)
        elif method == "euclidean":
            return self._euclidean_vector_similarity(vec1, vec2)
        elif method == "manhattan":
            return self._manhattan_vector_similarity(vec1, vec2)
        else:
            return self._cosine_vector_similarity(vec1, vec2)
    
    def calculate_comprehensive_similarity_v1(self, case1: Dict[str, Any], 
                                            case2: Dict[str, Any], 
                                            weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        計算綜合相似度 v1.0
        
        綜合考慮多個維度的相似度計算
        """
        default_weights = {
            'age': 0.15,
            'gender': 0.10,
            'symptoms': 0.40,
            'pulse': 0.20,  # v1.0
            'history': 0.15
        }
        
        if weights:
            default_weights.update(weights)
        
        similarities = {}
        
        # 年齡相似度
        if case1.get('age') and case2.get('age'):
            similarities['age'] = self.calculate_age_similarity(case1['age'], case2['age'])
        
        # 性別匹配
        if case1.get('gender') and case2.get('gender'):
            similarities['gender'] = 1.0 if case1['gender'] == case2['gender'] else 0.0
        
        # 症狀相似度
        symptoms1 = self._extract_symptoms(case1)
        symptoms2 = self._extract_symptoms(case2)
        if symptoms1 and symptoms2:
            similarities['symptoms'] = self.calculate_tcm_symptom_similarity_v1(symptoms1, symptoms2)
        
        # v1.0 脈診相似度
        pulse1 = case1.get('pulse_text', '') or case1.get('pulse_info', '')
        pulse2 = case2.get('pulse_text', '') or case2.get('pulse_info', '')
        if pulse1 and pulse2:
            similarities['pulse'] = self.calculate_pulse_similarity_v1(pulse1, pulse2)
        
        # 病史相似度
        history1 = case1.get('present_illness', '') or case1.get('medical_history', '')
        history2 = case2.get('present_illness', '') or case2.get('medical_history', '')
        if history1 and history2:
            similarities['history'] = self.calculate_text_similarity(history1, history2)
        
        # 計算加權綜合相似度
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dimension, similarity in similarities.items():
            if dimension in default_weights:
                weight = default_weights[dimension]
                weighted_sum += similarity * weight
                total_weight += weight
        
        overall_similarity = weighted_sum / total_weight if total_weight > 0 else 0.0
        similarities['overall'] = overall_similarity
        
        return similarities
    
    # 私有輔助方法
    def _preprocess_text(self, text: str) -> List[str]:
        """文本預處理"""
        # 移除標點符號和多餘空格
        cleaned_text = re.sub(r'[^\w\s]', ' ', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text.strip())
        
        # 分詞
        words = cleaned_text.split()
        
        # 過濾空詞和短詞
        words = [word for word in words if len(word) > 1]
        
        return words
    
    def _normalize_tcm_term(self, term: str) -> str:
        """標準化中醫術語"""
        # 移除常見修飾詞
        term = re.sub(r'(輕度|中度|重度|明顯|略微)', '', term)
        term = term.strip()
        
        # 同義詞映射
        synonyms_map = {
            '頭疼': '頭痛',
            '睡不著': '失眠',
            '睡眠不好': '失眠',
            '疲倦': '疲勞',
            '累': '疲勞',
            '胸口悶': '胸悶',
            '心跳快': '心悸'
        }
        
        return synonyms_map.get(term, term)
    
    def _extract_pulse_features(self, pulse_text: str) -> List[str]:
        """提取脈診特徵"""
        features = []
        
        # 脈診關鍵詞
        pulse_keywords = ['浮', '沉', '遲', '數', '滑', '澀', '弦', '緩', '細', '洪', '虛', '實']
        
        for keyword in pulse_keywords:
            if keyword in pulse_text:
                features.append(keyword)
        
        return features
    
    def _extract_symptoms(self, case: Dict[str, Any]) -> List[str]:
        """從案例中提取症狀"""
        symptoms = []
        
        # 從不同欄位提取症狀
        chief_complaint = case.get('chief_complaint', '')
        summary_text = case.get('summary_text', '')
        
        # 合併症狀文字
        symptom_text = f"{chief_complaint} {summary_text}"
        
        if symptom_text.strip():
            # 簡單分詞和症狀識別
            words = self._preprocess_text(symptom_text)
            
            # 過濾出症狀相關詞彙
            for word in words:
                if word in self.tcm_symptom_weights or len(word) >= 2:
                    symptoms.append(word)
        
        return symptoms
    
    def _jaccard_similarity(self, list1: List[str], list2: List[str]) -> float:
        """Jaccard 相似度"""
        set1, set2 = set(list1), set(list2)
        intersection = set1 & set2
        union = set1 | set2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _weighted_jaccard_similarity(self, list1: List[str], list2: List[str], 
                                   weights: Optional[Dict[str, float]] = None) -> float:
        """加權 Jaccard 相似度"""
        if not weights:
            return self._jaccard_similarity(list1, list2)
        
        set1, set2 = set(list1), set(list2)
        intersection = set1 & set2
        union = set1 | set2
        
        if not union:
            return 0.0
        
        # 計算加權交集和並集
        weighted_intersection = sum(weights.get(item, 1.0) for item in intersection)
        weighted_union = sum(weights.get(item, 1.0) for item in union)
        
        return weighted_intersection / weighted_union if weighted_union > 0 else 0.0
    
    def _cosine_similarity(self, list1: List[str], list2: List[str]) -> float:
        """文本餘弦相似度"""
        # 統計詞頻
        counter1 = Counter(list1)
        counter2 = Counter(list2)
        
        # 獲取所有詞彙
        all_words = set(counter1.keys()) | set(counter2.keys())
        
        # 構建向量
        vec1 = [counter1.get(word, 0) for word in all_words]
        vec2 = [counter2.get(word, 0) for word in all_words]
        
        return self._cosine_vector_similarity(vec1, vec2)
    
    def _cosine_vector_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """向量餘弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _euclidean_vector_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """歐幾里得距離相似度"""
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))
        max_distance = math.sqrt(sum(max(a, b) ** 2 for a, b in zip(vec1, vec2)))
        
        if max_distance == 0:
            return 1.0
        
        return max(0.0, 1.0 - distance / max_distance)
    
    def _manhattan_vector_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """曼哈頓距離相似度"""
        distance = sum(abs(a - b) for a, b in zip(vec1, vec2))
        max_distance = sum(max(abs(a), abs(b)) for a, b in zip(vec1, vec2))
        
        if max_distance == 0:
            return 1.0
        
        return max(0.0, 1.0 - distance / max_distance)
